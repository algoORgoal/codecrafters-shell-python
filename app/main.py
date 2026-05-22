import sys


def main():
    sys.stdout.write("$ ")
    command = input()

    if command == "exit":
        return

    print(f"{command}: command not found")

    main()


if __name__ == "__main__":
    main()
