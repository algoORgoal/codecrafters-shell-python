import sys
from typing import Callable
import os
import sys
from os import environ
from os import pathsep
from os import access
import subprocess
from collections import deque
import re
import readline
import signal

KEYBOARD_DICT = {
    'TAB': 'tab',
}

INTERACTION_DICT = {
    'COMPLETE': 'complete',
}

SHELL_BUILTIN_DICT = {
    'EXIT': 'exit',
    'ECHO': 'echo',
    'TYPE': 'type',
    "PWD": 'pwd',
    "CD": 'cd',
    'COMPLETE': 'complete',
    'JOBS': 'jobs',
    'DECLARE': 'declare',
}

EMPTY_STRING = ""

command_to_custom_completer_dict: dict[str, str] = {}
background_job_to_info_dict: dict[int, dict[str, str | int]] = {}


def main():
    delims = readline.get_completer_delims()
    readline.set_completer_delims(delims.replace("-", "").replace(os.sep, ""))
    register_command_autocomplete()

    signal.signal(signal.SIGCHLD, reap)

    while True:
        command_line = input("$ ")            

        should_redirect_stdout = check_should_redirect_stdout(command_line)
        should_append_stdout = check_should_append_stdout(command_line)
        should_redirect_stderr = check_should_redirect_stderr(command_line)
        should_append_stderr = check_should_append_stderr(command_line)
        
        command, (stdout_filename, append_stdout_filename), (stderr_filename, append_stderr_filename) = parse_stdout_and_stderr(command_line)
        
        tokens = parse_command(command)
        command_name, args = tokens[0], tokens[1:]

        should_run_background = check_should_run_background(command)

        if should_run_background == True:
            stdout = None
            if should_redirect_stdout:
                stdout = open(stdout_filename, "w")
            elif should_append_stdout:
                stdout = open(append_stdout_filename, "a")

            stderr = None
            if should_redirect_stderr:
                stderr = open(stderr_filename, "w")
            elif should_append_stderr:
                stderr = open(append_stderr_filename, "a")

            try:
                job_message = run_background(tokens, out=stdout, err=stderr)
                print(job_message)
            finally:
                if stdout is not None:
                    stdout.close()
                if stderr is not None:
                    stderr.close() 
            
            continue
            
        

        
        if command_name == SHELL_BUILTIN_DICT['EXIT']:
            break

        if command_name in SHELL_BUILTIN_DICT.values():
            stdout = None
            if should_redirect_stdout:
                stdout = open(stdout_filename, "w")
            elif should_append_stdout:
                stdout = open(append_stdout_filename, "a")

            stderr = None
            if should_redirect_stderr:
                stderr = open(stderr_filename, "w")
            elif should_append_stderr:
                stderr = open(append_stderr_filename, "a")

            try:
                run_builtin_command(command_name, args, stdout=stdout, stderr=stderr)
            finally:
                if stdout is not None:
                    stdout.close()
                if stderr is not None:
                    stderr.close() 
            
            continue
        
            
        executable_path = find_executable_path(command_name)
        if executable_path is not None:
            stdout = None
            if should_redirect_stdout:
                stdout = open(stdout_filename, "w")
            elif should_append_stdout:
                stdout = open(append_stdout_filename, "a")
                
            stderr = None
            if should_redirect_stderr:
                stderr = open(stderr_filename, "w")
            elif should_append_stderr:
                stderr = open(append_stderr_filename, "a")
                
            try:
                run_executable(command_name, args, stdout=stdout, stderr=stderr)
            finally:
                if stdout is not None:
                    stdout.close()
                if stderr is not None:
                    stderr.close()

            continue


        print(f"{command}: command not found")

def register_command_autocomplete():
    # mac에서는 라이선스 이슈로 gnu readline 구현체 대신 libedit readline을 사용한다.
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    readline.set_completer(master_completer)
    
        
def master_completer(text: str, state: int):
    line = readline.get_line_buffer()

    tokens = parse_command(line)
    command_name = tokens[0]    

    # command completion
    # fixme argument가 command name과 같으면 command name과 현재 token이 같을 수 있음. 예를 들어 cd 'cd'
    if text[readline.get_begidx():readline.get_endidx()] == command_name:
        return command_completer(text, state)

    # custom completion
    if command_name in command_to_custom_completer_dict:
        return custom_completer(text, state)
        
    # nested file completion
    if os.sep in text:
        return nested_file_completer(text, state)
    
    # file completion at current working directory
    return working_directory_file_completer(text, state)

def command_completer(text: str, state: int):
    matches = []
    match_to_type_dict = {}
    for command_name in SHELL_BUILTIN_DICT.values():
        if command_name.startswith(text):
            matches.append(command_name)
            match_to_type_dict[command_name] = "COMMAND"

        PATH = os.environ.get("PATH")
        
        if PATH is not None:
            directories = PATH.split(pathsep)
            for directory in directories:
                if access(directory, os.X_OK) == False:
                    continue
                for name in os.listdir(directory):
                    if name.startswith(text):
                        matches.append(name)
                        match_to_type_dict[name] = "COMMAND"
    
    return format_match(matches, state, match_to_type_dict)

def custom_completer(text: str, state: int):
    matches = []
    match_to_type_dict = {}

    line = readline.get_line_buffer()
    start_index = readline.get_begidx()
    end_index = readline.get_endidx()

    tokens = parse_command(line[:start_index])
    previous = tokens[-1] if len(tokens) > 0 else None


    command_name = tokens[0]

    env = create_env({
        "COMP_LINE": line,
        "COMP_POINT": end_index,
    })
    

    try:
        path = command_to_custom_completer_dict[command_name]
        output = subprocess.run([path, command_name, text, previous], capture_output=True, text=True, env=env)
    except OSError as e:
        print(e)
    
    if output.stdout != EMPTY_STRING:
        for match in output.stdout.strip(os.linesep).split(os.linesep):
            matches.append(match)
            match_to_type_dict[match] = "CUSTOM"
    
    

    return format_match(matches, state, match_to_type_dict)

def create_env(table):
    env = os.environ.copy()
    for key in table:
        value = table[key]
        env[key] = str(value)
    return env
    
    

def nested_file_completer(text: str, state: int):
    matches = []
    match_to_type_dict = {}

    directory_path, prefix = os.sep.join(text.split(os.sep)[:-1]), text.split(os.sep)[-1]
    
    if directory_path.startswith(os.sep): # already absolute directory
        absolute_path = directory_path
    else: # relative directory
        path_segments = directory_path.strip(os.sep).split(os.sep)
        absolute_path = resolve_to_absolute_path(os.getcwd(), deque(path_segments))
    
    if os.path.isdir(absolute_path) == True:
        for name in os.listdir(absolute_path):
            if name.startswith(prefix):
                match_path = f"{directory_path}{os.sep}{name}"
                matches.append(match_path)
                match_to_type_dict[match_path] = "DIRECTORY" if os.path.isdir(match_path) else "FILE"
    
    return format_match(matches, state, match_to_type_dict)

def working_directory_file_completer(text: str, state: int):
    matches = []
    match_to_type_dict = {}

    working_directory = os.getcwd()
    for name in os.listdir(working_directory):
        if name.startswith(text):
            matches.append(name)
            match_path = f"{working_directory}{os.sep}{name}"
            match_to_type_dict[name] = "DIRECTORY" if os.path.isdir(match_path) else "FILE"
    
    return format_match(matches, state, match_to_type_dict)

def format_match(matches: list[str], state: int, match_to_type_dict: dict[str, str]):
    if len(matches) <= state:
        return None
    if match_to_type_dict[matches[state]] == "DIRECTORY":
        return f"{matches[state]}{os.sep}"
    else:
        return f"{matches[state]} "

    
    




def run_builtin_command(command_name, args, stdout=None, stderr=None):
    try:
        output = None
        if command_name == SHELL_BUILTIN_DICT['ECHO']:
            output = echo(args)
            
        elif command_name == SHELL_BUILTIN_DICT['TYPE']:
            output = type(args, set(SHELL_BUILTIN_DICT.values()))

        elif command_name == SHELL_BUILTIN_DICT['PWD']:
            output = pwd(args)  

        elif command_name == SHELL_BUILTIN_DICT['CD']:
            cd(args)
        
        elif command_name == SHELL_BUILTIN_DICT['COMPLETE']:
            output = complete(args)

        elif command_name == SHELL_BUILTIN_DICT['JOBS']:
            output = jobs()

        elif command_name == SHELL_BUILTIN_DICT['DECLARE']:
            output = declare(args)

        if stdout is None and output is None:
            return

        if output is None:
            print("", file=stdout)
            return
        
        print(output, file=stdout)
        

    except Exception as e:
        print(e, file=stderr)

def parse_stdout_and_stderr(command_line: str):
    command_line, stdout_filename = parse_redirection_stdout(command_line)
    command_line, append_stdout_filename = parse_append_stdout(command_line)
    command_line, stderr_filename = parse_redirection_stderr(command_line)
    command, append_stderr_filename = parse_append_stderr(command_line)

    return command, (stdout_filename, append_stdout_filename), (stderr_filename, append_stderr_filename)


def check_should_redirect_stdout(command):
    return " > " in command or " 1> " in command

def check_should_append_stdout(command):
    return " >> " in command or " 1>> " in command

def check_should_redirect_stderr(command):
    return " 2> " in command

def check_should_append_stderr(command):
    return " 2>> " in command



def parse_redirection_stdout(command: str):
    if ' > ' in command:
        match = re.search(r'>[\s]+[\S]+', command)
        filename = re.sub(r'>[\s]+', '', command[match.start():match.end()])
        command = command[:match.start()] + command[match.end():]
        return command, filename
    
    if ' 1> ' in command:
        match = re.search(r'1>[\s]+[\S]+', command)
        filename = re.sub(r'1>[\s]+', '', command[match.start():match.end()])
        command = command[:match.start()] + command[match.end():]
        return command, filename
        

    return command, None

def parse_append_stdout(command: str):
    if ' >> ' in command:
        match = re.search(r'>>[\s]+[\S]+', command)
        filename = re.sub(r'>>[\s]+', '', command[match.start():match.end()])
        command = command[:match.start()] + command[match.end():]
        return command, filename
    
    if ' 1>> ' in command:
        match = re.search(r'1>>[\s]+[\S]+', command)
        filename = re.sub(r'1>>[\s]+', '', command[match.start():match.end()])
        command = command[:match.start()] + command[match.end():]
        return command, filename
        

    return command, None
    
def parse_redirection_stderr(command: str):
    if ' 2> ' in command:
        match = re.search(r'2>[\s]+[\S]+', command)
        filename = re.sub(r'2>[\s]+', '', command[match.start():match.end()])
        command = command[:match.start()] + command[match.end():]
        return command, filename
    
    return command, None

def parse_append_stderr(command: str):
    if ' 2>> ' in command:
        match = re.search(r'2>>[\s]+[\S]+', command)
        filename = re.sub(r'2>>[\s]+', '', command[match.start():match.end()])
        command = command[:match.start()] + command[match.end():]
        return command, filename
    
    return command, None



def echo(args):
    return ' '.join(args)



def parse_command(string: str) -> list[str]:
    tokens = []
    in_single_quote = False
    in_double_quote = False
    should_escape = False
    token = EMPTY_STRING

    for char in string:
        if should_escape == True:
            token += char
            should_escape = False     

        elif in_single_quote == True:
            if char == "'":
                in_single_quote = False
            else:
                token += char
        elif in_double_quote == True:
            if char == '"':
                in_double_quote = False
            elif char in ['"', '\\', '$', '`',]:
                should_escape = True
            else:
                token += char
        else:
            if char == " ":
                if token != EMPTY_STRING:
                    tokens.append(token)
                    token = EMPTY_STRING
            elif char == "'":
                in_single_quote = True
            elif char == '"':
                in_double_quote = True
            elif char == "\\":
                should_escape = True
            else:
                token += char
    
    
    if token != EMPTY_STRING:
        tokens.append(token)

    return tokens

def find_executable_path(command_name):
    PATH = environ.get("PATH")
    if PATH is None:
        return None

    directories = PATH.split(pathsep)
    for directory in directories:
        path = f"{directory}{os.sep}{command_name}"
        if access(path, os.X_OK) == True:
            return path

    return None


def type(args, built_ins):
    text = ' '.join(args)
    if text in built_ins:
        return f"{text} is a shell builtin"

    executable_path = find_executable_path(text)
    if executable_path is not None:
        return f"{text} is {executable_path}"

    return f"{text}: not found"


def run_executable(command_name, args, stdout = None, stderr=None):
    subprocess.run([command_name] + args, stdout=stdout, stderr=stderr)


def pwd(args):
    return os.getcwd()


def cd(args):
    directory_path: str = args[0]
    
    if directory_path[0] == '/': # already absolute directory
        absolute_path = directory_path
    else: # relative directory
        path_segments = directory_path.strip(pathsep).split(os.sep)
        absolute_path = resolve_to_absolute_path(os.getcwd(), deque(path_segments))

    if os.path.isdir(absolute_path) == False:
        print(f"cd: {directory_path}: No such file or directory")
        return
        
    os.chdir(absolute_path)

def resolve_to_absolute_path(current, path_segments):
    if len(path_segments) == 0:
        return current

    path_segment = path_segments.popleft() 

    DIRECTORY_ALIAS = {
        'WORKING': '.',
        'PARENT': '..',
        'HOME': '~',
    }

    if path_segment == DIRECTORY_ALIAS['WORKING']:
        absolute_path = current
    elif path_segment == DIRECTORY_ALIAS['PARENT']:
        parent_directory = os.path.dirname(current)
        absolute_path = parent_directory
    elif path_segment == DIRECTORY_ALIAS['HOME']:
        home_directory = os.environ.get('HOME')
        absolute_path = home_directory
    else:
        absolute_path = f"{current}{os.sep}{path_segment}"

    return resolve_to_absolute_path(absolute_path, path_segments)

def complete(args):
    queue = deque(args)

    while len(queue) > 0:
        arg = queue.popleft()
        if arg.startswith("-") or arg.startswith("--"):
            option = arg
        
            if option == "-C":
                # todo handle relative path
                # todo check if the file exists and is executable
                path_to_completer = queue.popleft()
                command_name = queue.popleft()
                command_to_custom_completer_dict[command_name] = path_to_completer

            
            elif option == "-p":
                command_name = queue.popleft()
                if command_name in command_to_custom_completer_dict:
                    path = command_to_custom_completer_dict[command_name]
                    return f"complete -C '{path}' {command_name}"
                else:
                    return f"complete: {command_name}: no completion specification"

            elif option == "-r":
                command_name = queue.popleft()

                if command_name in command_to_custom_completer_dict:
                    del command_to_custom_completer_dict[command_name]

def jobs():
    output = []
    to_be_deleted = []

    for job_number, info in background_job_to_info_dict.items():
        recency = calculate_job_recency(job_number)
        
        if recency == 0:
            status_symbol = "+"
        elif recency == 1:
            status_symbol = "-"
        else:
            status_symbol = " "

        if info["status"] == "Running":
            should_print_ampersand = True
        else:
            should_print_ampersand = False

        if should_print_ampersand:
            command_str = ' '.join(info['command'] + ['&'])
        else:
            command_str = ' '.join(info['command'])

        output.append(f"[{job_number}]{status_symbol}  {info["status"].ljust(24)}{command_str}")

        if info["status"] == "Done":
            to_be_deleted.append(job_number)

    for job_number in to_be_deleted:
        del background_job_to_info_dict[job_number]

    if len(output) == 0:
        return None
    
    return os.linesep.join(output)

def calculate_job_recency(job_number):
    sorted_job_numbers = sorted([job_number for job_number in background_job_to_info_dict], reverse=True)
    return sorted_job_numbers.index(job_number)




def check_should_run_background(command: str):
    tokens = parse_command(command)
    return tokens[-1] == '&'

def run_background(args: list[str], out: str | None, err: str | None):
    # todo: it should run the command using this shell instead of system shell
    # currently it just runs the command using the system shell
    process = subprocess.Popen(args[:-1], stdout=out, stderr=err)
    job_number = len(background_job_to_info_dict) + 1
    background_job_to_info_dict[job_number] = {"pid": process.pid, "command": args[:-1], "status": "Running"}

    return f"{[job_number]} {background_job_to_info_dict[job_number]["pid"]}"
        
        

def declare(args):
    queue = deque(args)

    while len(queue) > 0:
        arg = queue.popleft()
        if arg.startswith("-") or arg.startswith("--"):
            option = arg

            if option == "-p":
                variable_name = queue.popleft()
                return f"declare: {variable_name}: not found"

def reap(signum, frame):
    ANY_CHILD_PROCESS = -1
    NO_WAIT = os.WNOHANG

    try:
        pid, status = os.waitpid(ANY_CHILD_PROCESS, NO_WAIT)
        
        # no terminated child processes
        if pid == 0:
            return
        
        for job_number, info in background_job_to_info_dict.items():
            if info["pid"] == pid:
                info["status"] = "Done"
                break
    
    except ChildProcessError: # no more child processes
        pass
            



    
        



if __name__ == "__main__":
    main()


# 1. " > "이 command 안에 있는지 확인
# 2. 안에 있으면 " > " 기준으로 명령어 쪼개기
# 3. 첫번째 파트 명령어 수행
# 4. 첫번째 파트 명령어의 수행 결과를, 출력하는 대신에 output.txt에 저장

# 문제: custom cli에 대해서도 >를 분리하도록 처리를 해버린다.
# 해결방안: custom cli는 따로 파싱하도록 분기 처리한다.

# 문제: subprocess.run에 >를 인자로 줬을 때 special character로 해석되지 않는다.
# 해결방법: 표준 출력을 파일로 연결한다.

# 문제: subprocess.run의 매개변수 전달방식이 잘못되었다.
# 해결방법: subprocess.run(command, stdout=stdout)으로 키워드 인자로 설정해준다.

# 문제: file.write은 \n문제를 자동으로 붙이지 않음
# 해결방법: print(string, file=f)를 f.write() 대신 사용한다.

# 문제: stderr을 파일에 연결할 수 있어야 함, stdout과 stderr이 동시에 주어지는 경우도 있음
# 해결 방법: subprocess.run의 stderr을 2> file에 연결한다.

# 문제: echo List of files: > bar.md에 쓰기할 때 close 실패함
# 원인: stdout이 append가 안 될 때 None으로 전환되어서, 기존 참조를 잃어버림
# 해결방법: 조건문으로 분기 처리

# 문졔: absolute directory를 결과에 사용하면 상대경로가 절대경로로 변환된다.
# 해결방법: 
#   입력으로 주어지는 디렉토리를 결과물에 사용한다.
#   이 때, 경로 중 디렉토리 부분만 추출해야 하고, 이 때 자연스럽게 filename prefix를 구할 수 있다.
#   os.sep을 사용하여 운영체제와 독립적으로 실행한다.

# 문제: 디렉토리 자동완성인 경우 separator 추가하고, space 붙이지 않아야 한다.
# 해결 방법: 각 상태가 directory인지 file인지 구분하는 딕셔너리를 만든다.
#          출력 형식을 결정하는 로직과 match 결과를 반환하는 로직을 분리한다.

# 문제: custom completer를 만들어야 한다. linebreak를 기준으로 끊어서 반환한 값이 후보자가 된다.
# 해결방법: 처음과 끝에 있는 linebreak를 제거하고 linebreak 기준으로 split한 것을 matches에 넣기. 운영체제 독립적으로 
#         작동하도록 os.linesep를 사용한다.

# 문제: sys.executable로 설명하면 python script만 completer로 실행 가능하다.
# 해결방안: sys.executable을 빼면 쉘에서 실행 가능한 script를 모두 실행할 수 있다.

# 문제: custom output을 모두 출력한 뒤에 space를 출력해야 한다.
# 해결방법: custom completer로 따로 로직을 분리한 다음에, 출력은 format_match로 처리한다.

# 문제: 로컬에서 테스트할 때는 subprocess를 shell로 실행할 때 permission denied error가 발생한다.
# 해결방법: shell=True 옵션을 넣어서 실행한다. 그러면 OS 직접 수행시 권한 막히는 거 해결 가능