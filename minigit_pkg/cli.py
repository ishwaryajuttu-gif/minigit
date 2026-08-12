import sys
from minigit_pkg import repository

def main():
    if len(sys.argv) < 2:
        print("Usage: minigit <command> [args]")
        return

    command = sys.argv[1]

    if command == "init":
        repository.init()
    elif command == "add":
        if len(sys.argv) < 3:
            print("Usage: minigit add <filepath>")
            return
        repository.add(sys.argv[2])
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()