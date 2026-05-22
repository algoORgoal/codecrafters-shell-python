import sys


def main():
    sys.stdout.write("$ ")
    command = input()
    parts = command.split()
    command_name, rest = parts[0], parts[1:]

    SHELL_BUILTIN_DICT = {
        'EXIT': 'exit',
        'ECHO': 'echo',
        'TYPE': 'type',
    }

    if command_name == SHELL_BUILTIN_DICT['EXIT']:
        return
    elif command_name == SHELL_BUILTIN_DICT['ECHO']:
        echo(' '.join(rest))
    elif command_name == SHELL_BUILTIN_DICT['TYPE']:
        type(' '.join(rest), set(SHELL_BUILTIN_DICT.values()))
    else:
        print(f"{command}: command not found")

    main()


def echo(text):
    print(text)


def type(text, built_ins):
    if text in built_ins:
        print(f"{text} is a shell builtin")
    else:
        print(f"{text}: not found")


if __name__ == "__main__":
    main()
