import sys
from minigit_pkg import repository

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: minigit <command> [args]")
        return 1

    command = sys.argv[1]

    try:
        if command == "init":
            repository.init()
        elif command == "add":
            if len(sys.argv) < 3:
                print("Usage: minigit add <filepath>...")
                return 1
            repository.add(*sys.argv[2:])
        elif command == "commit":
            if len(sys.argv) != 4 or sys.argv[2] != "-m":
                print('Usage: minigit commit -m "message"')
                return 1
            message = sys.argv[3]
            repository.commit(message)
        elif command == "log":
            repository.log()
        elif command == "config":
            args = sys.argv[2:]
            use_global = "--global" in args
            args = [arg for arg in args if arg != "--global"]
            if len(args) not in (1, 2):
                print("Usage: minigit config [--global] <key> [<value>]")
                return 1
            repository.config(args[0], args[1] if len(args) == 2 else None, use_global)
        elif command == "checkout":
            args = sys.argv[2:]
            force = "--force" in args
            args = [arg for arg in args if arg != "--force"]
            if not args:
                print("Usage: minigit checkout <commit> [<file>...] [--force]")
                return 1
            repository.checkout(args[0], *args[1:], force=force)
        else:
            print(f"Unknown command: {command}")
            return 1
    except repository.MinigitError as error:
        print(f"Error: {error}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
