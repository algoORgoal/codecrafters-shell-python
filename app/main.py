import os
import sys
from os import environ
from os import pathsep
from os import access
import subprocess


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
        parts = command.split()
        command_name, args = parts[0], parts[1:]

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
    absolute_directory = args[0]

    if os.path.isdir(absolute_directory) == False:
        print(f"cd: {absolute_directory}: No such file or directory")
        return

    os.chdir(absolute_directory)


if __name__ == "__main__":
    main()
