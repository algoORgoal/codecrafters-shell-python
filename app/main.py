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

def main():
    SHELL_BUILTIN_DICT = {
        'EXIT': 'exit',
        'ECHO': 'echo',
        'TYPE': 'type',
        "PWD": 'pwd',
        "CD": 'cd',
    }

    while True:
        sys.stdout.write("$ ")
        command = input()
        end_index = command.find(" ")

        if end_index == -1:
            command_name = command
            args = []
        else:
            command_name = command[:end_index]
            text = command[end_index:].strip()
            args = parse_arguments(text)

        if command_name == SHELL_BUILTIN_DICT['EXIT']:
            break

        if command_name == SHELL_BUILTIN_DICT['ECHO']:
            echo(args)
            continue

        if command_name == SHELL_BUILTIN_DICT['TYPE']:
            type(args, set(SHELL_BUILTIN_DICT.values()))
            continue

        if command_name == SHELL_BUILTIN_DICT['PWD']:
            pwd(args)
            continue

        if command_name == SHELL_BUILTIN_DICT['CD']:
            cd(args)
            continue

        executable_path = find_executable_path(command_name)
        if executable_path is not None:
            run_executable(command_name, args)
            continue

        print(f"{command}: command not found")


def echo(args):
    print(' '.join(args))



def parse_arguments(string):
    args = []
    in_single_quote = False
    in_double_quote = False
    should_treat_literally = False
    token = ""

    for char in string:
        if in_single_quote == True:
            if char == "'":
                in_single_quote = False
            else:
                token += char
        elif in_double_quote == True:
            if char == '"':
                in_double_quote = False
            else:
                token += char
        else:

            if should_treat_literally == True:
                token += char
                should_treat_literally = False                
            elif char == " ":
                if token != "":
                    args.append(token)
                    token = ""
            elif char == "'":
                in_single_quote = True
            elif char == '"':
                in_double_quote = True
            elif char == "\\":
                should_treat_literally = True
            else:
                token += char
    
    
    if token != "":
        args.append(token)

    return args

    

    


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
        print(f"{text} is a shell builtin")
        return

    executable_path = find_executable_path(text)
    if executable_path is not None:
        print(f"{text} is {executable_path}")
        return

    print(f"{text}: not found")


def run_executable(command_name, args):
    subprocess.run([command_name] + args)


def pwd(args):
    print(os.getcwd())


def cd(args):
    directory_path: str = args[0]
    
    if directory_path[0] == '/': # already absolute directory
        absolute_path = directory_path
    else: # relative directory
        path_segments = directory_path.strip('/').split('/')
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
