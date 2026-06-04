import os
import sys
from os import environ
from os import pathsep
from os import access
import subprocess
from collections import deque

# 1. stack is empty and character is ' => push
# 2. stack is empty and character is space 

# 'hello   world' => 'hello   world'
# hello   world => hello   world
# hello   'world' => hello world
# hello'world' => helloworld
# hello'world'hello => helloworldhello
# ' => 시작
# ' => 종료
# quote 안에 들어있지 않은 space => 무시

# abc'hello'world
# 1. len(stack) == 0 and space => 갖다 버림


# 'hello world'

# echo를 제외한 다른 명령어의 경우에는
# args= [ result for result in results if result != ' ']
# 를 넣으면 되지 않냐?

# echo 'hello  /'  world' hello world

# 'abc'

# 1. stack에 뭐가 들어있음
# 2. stack의 bottom에 quote가 있음

# abc'def'

# 1. stack에 뭐가 들어있는 상태
# 2. stack의 bottom에 quote가 없음

# abc'def' 'ghi'
# ['abcdef', 'ghi']

SHELL_BUILTIN_DICT = {
    'EXIT': 'exit',
    'ECHO': 'echo',
    'TYPE': 'type',
    "PWD": 'pwd',
    "CD": 'cd',
}

EMPTY_STRING = ""

def main():
    

    while True:
        sys.stdout.write("$ ")
        command_line = input()
        should_redirect = check_should_redirect(command_line)

        if should_redirect == True:
            command, filename = parse_redirection(command_line)

        tokens = parse_command(command)
        command_name, args = tokens[0], tokens[1:]

        if command_name == SHELL_BUILTIN_DICT['EXIT']:
            break

        if command_name in SHELL_BUILTIN_DICT.values():
            output = run_builtin_command(command_name, args)
            if should_redirect:
                with open(filename, "w") as f:
                    print(output if output is not None else "", file=f)
            else:
                if output is not None:
                    print(output)
            
            continue
        
        executable_path = find_executable_path(command_name)
        if executable_path is not None:
            if should_redirect:
                with open(filename, "w") as f:
                    run_executable(command_name, args, f)
            else:
                run_executable(command_name, args)

            continue


        print(f"{command}: command not found")

def run_builtin_command(command_name, args):
    if command_name == SHELL_BUILTIN_DICT['ECHO']:
        output = echo(args)
        return output
            
    if command_name == SHELL_BUILTIN_DICT['TYPE']:
        output = type(args, set(SHELL_BUILTIN_DICT.values()))
        return output

    if command_name == SHELL_BUILTIN_DICT['PWD']:
        output = pwd(args)
        return output

    if command_name == SHELL_BUILTIN_DICT['CD']:
        cd(args)
        return None


def check_should_redirect(command):
    return " > " in command or " 1> " in command


def parse_redirection(command):
    if " > " in command:
        subcommand, filename = command.split(" > ")
        return subcommand, filename

    if " 1> " in command:
        subcommand, filename = command.split(" 1> ")
        return subcommand, filename
    
    return command, None


def echo(args):
    return ' '.join(args)



def parse_command(string):
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

        
    

    


# echo 'hello      world' => hello      world
# echo hello      world => hello world
# echo 'hello''world' => helloworld
# echo hello''world => helloworld

# def parse_arguments(string: str):
#     stack = []
#     for char in string:
#         if len(stack) == 0:
#             if char == ' ':
#                 continue
#             else:
#                 stack.append(char)
#         else:


def find_executable_path(command_name):
    PATH = environ.get("PATH")
    if PATH is None:
        return None

    directories = PATH.split(pathsep)
    for directory in directories:
        path = directory + "/" + command_name
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


def run_executable(command_name, args, stdout = None):
    subprocess.run([command_name] + args, stdout=stdout)


def pwd(args):
    return os.getcwd()


def cd(args):
    directory_path: str = args[0]
    
    if directory_path[0] == '/': # already absolute directory
        absolute_path = directory_path
    else: # relative directory
        path_segments = directory_path.strip(pathsep).split(pathsep)
        absolute_path = resolve_to_absolute_path(os.getcwd(), deque(path_segments))

    if os.path.isdir(absolute_path) == False:
        print(f"cd: {directory_path}: No such file or directory")
        return
        
    os.chdir(absolute_path)


# split path into path segments
# if the path segment is working directory => return current
# if the path semgent is parent => return parent
# if the path segment is a directory
# if current is None and the path segment is PARENT => pwd + parent

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
        absolute_path = current + '/' + path_segment

    return resolve_to_absolute_path(absolute_path, path_segments)


if __name__ == "__main__":
    main()


# 문제: path가 /로 시작하는 경우 root directory에서 시작한다.
#      path가 /로 시작하지 않는 경우 current working directory에서 시작한다.
# 해결방안: path가 /로 시작하는 경우 이미 절대경로이다.
#         path가 /로 시작하는 경우에만 상대경로이고, 이를 절대경로로 변환한다.


# single quotes
# 'hello  world' => single quote string literal is considered a single argument,
# while prevsing whitespaces.
# 'hello' world' quoted strings are considered as a single argument
# hello '' world => empty quotes are ignored

# stack으로 쉽게 해결이 안 된다
# state machine으로 해결해야 한다.
# single quote 안에 있다 => in_single_quote = True
# single quote 안에 있는 상태가 아니다 => in_single_quote = False
# 
# while char in string:
#  if in_single_quote == False and char == " ":
#    if token != "":
#      args.append(token)
#      token = ""
#  elif in_single_quote == False and char == "'":
#    in_single_quote = True
#    token += char
#  elif in_single_quote == False:
#    token += char
#  elif in_single_quote == True and char == "'":
#    in_single_quote = False
#    args.append(token)
#    token = ""
#  else:
#    token += char
#  

#    
#  if in


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