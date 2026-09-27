import sys
from minigit_pkg import repository

HELP_FLAGS = ("--help", "-h")

# command: (usage, one-line summary, extra detail for 'minigit <command> --help')
COMMANDS = {
    "init": (
        "minigit init",
        "Create an empty repository in the current folder",
        "",
    ),
    "add": (
        "minigit add <file>...",
        "Stage files for the next commit",
        "Re-adding a changed file replaces its staged version, and adding a tracked\n"
        "file that was deleted stages its removal. If any file can't be added,\n"
        "nothing is staged.",
    ),
    "commit": (
        'minigit commit -m "message"',
        "Record the staged files as a new commit",
        "The commit records your name, email and the current time; set them with\n"
        "'minigit config'. Refuses if nothing changed since the last commit.",
    ),
    "log": (
        "minigit log",
        "Show the commit history, oldest first",
        "Each commit is shown with its hash, author, date and message.",
    ),
    "checkout": (
        "minigit checkout <commit> [<file>...] [--force]",
        "Restore files from a commit and stage them",
        "<commit> is HEAD, a hash from 'log', or its first 4 or more characters.\n"
        "With no files, the whole snapshot is restored. Files with changes that\n"
        "aren't staged are never overwritten unless you pass --force.\n"
        "Commit afterwards to record the restored files.",
    ),
    "config": (
        "minigit config [--global] <key> [<value>]",
        "Set or show user.name and user.email",
        "With a value, sets <key>; without one, shows it. --global applies the\n"
        "setting to all your repositories instead of just this one.",
    ),
}


def general_help() -> str:
    width = max(len(usage) for usage, _, _ in COMMANDS.values()) - len("minigit ") + 2
    lines = [
        "Usage: minigit <command> [<args>]",
        "",
        "A from-scratch reimplementation of Git's core storage engine.",
        "",
        "Commands:",
    ]
    for usage, summary, _ in COMMANDS.values():
        lines.append(f"  {usage[len('minigit '):]:<{width}}{summary}")
    lines += ["", "Run 'minigit <command> --help' for details on one command."]
    return "\n".join(lines)


def command_help(command: str) -> str:
    usage, summary, detail = COMMANDS[command]
    text = f"Usage: {usage}\n\n{summary}."
    return f"{text}\n\n{detail}" if detail else text


def usage_error(command: str) -> int:
    print(f"Usage: {COMMANDS[command][0]}")
    return 1


def main() -> int:
    if len(sys.argv) < 2:
        print(general_help())
        return 1

    command = sys.argv[1]
    args = sys.argv[2:]

    if command in HELP_FLAGS or command == "help":
        if command == "help" and args:
            if len(args) > 1 or args[0] not in COMMANDS:
                print(f"Unknown command: {' '.join(args)}\nRun 'minigit --help' to see the commands.")
                return 1
            print(command_help(args[0]))
        else:
            print(general_help())
        return 0
    if command not in COMMANDS:
        print(f"Unknown command: {command}\nRun 'minigit --help' to see the commands.")
        return 1
    # Only the first argument counts as a help flag, so 'commit -m --help' still commits
    if args and args[0] in HELP_FLAGS:
        print(command_help(command))
        return 0

    try:
        if command == "init":
            if args:
                return usage_error(command)
            repository.init()
        elif command == "add":
            if not args:
                return usage_error(command)
            repository.add(*args)
        elif command == "commit":
            if len(args) != 2 or args[0] != "-m":
                return usage_error(command)
            repository.commit(args[1])
        elif command == "log":
            if args:
                return usage_error(command)
            repository.log()
        elif command == "config":
            use_global = "--global" in args
            args = [arg for arg in args if arg != "--global"]
            if len(args) not in (1, 2):
                return usage_error(command)
            repository.config(args[0], args[1] if len(args) == 2 else None, use_global)
        elif command == "checkout":
            force = "--force" in args
            args = [arg for arg in args if arg != "--force"]
            if not args:
                return usage_error(command)
            repository.checkout(args[0], *args[1:], force=force)
    except repository.MinigitError as error:
        print(f"Error: {error}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
