import sys


def main():
    sys.stdout.write("$ ")
    command = input()
    command_name = command.split()[0]

    if command_name == "exit":
        return
    elif command_name == "echo":
        echo(command)
    else:
        print(f"{command}: command not found")

    main()


def echo(text):
    command_name = "echo"
    if text.startswith(command_name):
        echo(text[len(command_name):])
        return

    space = " "

    if text.startswith(space):
        echo(text[len(space):])
        return

    print(text)


if __name__ == "__main__":
    main()
