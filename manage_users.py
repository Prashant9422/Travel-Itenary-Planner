import argparse
import getpass
import sys

from app.services.auth_service import create_user


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage planner user accounts.")
    commands = parser.add_subparsers(dest="command", required=True)
    create_user_command = commands.add_parser(
        "create-user", help="Create an account that can sign in to the app."
    )
    create_user_command.add_argument("username")
    args = parser.parse_args()

    password = getpass.getpass("New password (at least 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    try:
        create_user(args.username, password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created user '{args.username}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
