"""Provision console login accounts.

No self-registration by design -- this is an internal knowledge dashboard,
not a public app, so accounts are created out-of-band by whoever operates
it. Password normally comes from a masked `getpass` prompt (never a CLI
argument that'd land in shell history). Some terminals (remote-desktop
sessions, certain terminal emulators) don't support masked console reads at
all -- keystrokes silently don't register, which looks like "I can't type
the password" rather than an error. If that happens, set MANAGE_USERS_PASSWORD
in the environment instead (plain PowerShell variable assignment, not a
masked read, so it always works) -- still never a bare CLI argument.

    python manage_users.py add nehal "Nehal" reviewer --actor act-reviewer-nehal
    python manage_users.py add santosh "Santosh Thota" reviewer --actor act-reviewer-santosh
    python manage_users.py add dana "Dana Reyes" reviewer --actor act-reviewer-dana
    python manage_users.py add priya "Priya Nandakumar" reviewer --actor act-reviewer-priya
    python manage_users.py add ashok "Ashok Suthar" reviewer --actor act-reviewer-ashok
    python manage_users.py list

    # if getpass won't accept input in your terminal:
    #   PowerShell:  $env:MANAGE_USERS_PASSWORD = "your-password"
    #                python manage_users.py add nehal "Nehal" reviewer --actor act-reviewer-nehal
    #                Remove-Item Env:\\MANAGE_USERS_PASSWORD   # clear it afterward
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

import auth


def _read_password(username: str) -> str:
    env_password = os.environ.get("MANAGE_USERS_PASSWORD")
    if env_password is not None:
        print("(using MANAGE_USERS_PASSWORD from environment -- remember to clear it afterward)")
        return env_password
    password = getpass.getpass(f"Password for '{username}': ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("passwords did not match")
    return password


def cmd_add(args: argparse.Namespace) -> None:
    if args.role != "reviewer" and args.actor:
        print(f"warning: role '{args.role}' has no use for --actor, ignoring", file=sys.stderr)
        args.actor = None
    if args.role == "reviewer" and not args.actor:
        raise SystemExit("--actor is required for role 'reviewer' (must match a Cedar actor id, e.g. act-reviewer-nehal)")

    password = _read_password(args.username)
    if len(password) < 8:
        raise SystemExit("password must be at least 8 characters")

    auth.init_db()
    auth.create_user(args.username, password, args.display_name, args.role, args.actor)
    print(f"OK: {args.username} ({args.role}){' -> ' + args.actor if args.actor else ''}")


def cmd_list(_args: argparse.Namespace) -> None:
    auth.init_db()
    for u in auth.list_users():
        print(f"{u.username:12} {u.role:10} {u.display_name:24} {u.actor_id or '-'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="create or update a login account")
    p_add.add_argument("username")
    p_add.add_argument("display_name")
    p_add.add_argument("role", choices=auth.ROLES)
    p_add.add_argument("--actor", help="Cedar actor id this login maps to (required for role=reviewer)")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list provisioned accounts")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
