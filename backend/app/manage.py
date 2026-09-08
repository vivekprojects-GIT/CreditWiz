"""Local account provisioning and authored metadata validation.

Run from backend: python -m app.manage --help
No passwords are accepted in command-line arguments or written to output.
"""

import argparse
import getpass
import json
import uuid

from . import auth, database
from .identity import DirectoryProfile


def provision(email, name, role, department, groups, password):
    if len(password) < 12:
        raise ValueError("Use a password of at least 12 characters.")
    email = email.strip().lower()
    if "@" not in email:
        raise ValueError("A valid email is required.")
    with database.connect(write=True) as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email=?", (email,)
        ).fetchone()
        uid = existing[0] if existing else uuid.uuid4().hex
        profile = DirectoryProfile(
            id=uid,
            email=email,
            name=name,
            first_name=name.split()[0],
            initials="".join(p[0] for p in name.split())[:2],
            job_title=role,
            department=department,
            groups=groups,
        )
        conn.execute(
            "INSERT INTO users(id,email,password_hash,profile) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET email=excluded.email,password_hash=excluded.password_hash,profile=excluded.profile,active=1",
            (uid, email, auth.password_hash(password), profile.model_dump_json()),
        )
        conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
    return uid


def validate():
    from .learning.router import _raw
    from .marketplace.store import _read_json, normalize_agent
    from .marketplace.models import Agent

    agents = [
        Agent.model_validate(normalize_agent(a)) for a in _read_json("agents.json")
    ]
    if len({a.id for a in agents}) != len(agents):
        raise ValueError("Duplicate agent IDs")
    # Validate the authored graph without loading user state or exposing hidden data.
    from .learning.router import validate_catalog

    paths, items = validate_catalog(_raw())
    agent_ids = {a.id for a in agents}
    for item in items:
        if any(a not in agent_ids for a in item.related_agents):
            raise ValueError(f"Unknown related agent in {item.id}")
    return {"agents": len(agents), "learning_items": len(items), "paths": len(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "validate",
        help="Validate all authored catalog records and prerequisite references",
    )
    user = commands.add_parser(
        "user", help="Create or update a local account; revokes its prior sessions"
    )
    user.add_argument("--email", required=True)
    user.add_argument("--name", required=True)
    user.add_argument("--role", required=True)
    user.add_argument("--department", default="")
    user.add_argument(
        "--group",
        action="append",
        default=None,
        help="Repeat for each authorized group",
    )
    args = parser.parse_args()
    if args.command == "validate":
        print(json.dumps(validate(), indent=2))
    else:
        password = getpass.getpass("Password (12+ characters): ")
        if password != getpass.getpass("Confirm password: "):
            raise ValueError("Passwords do not match.")
        uid = provision(
            args.email,
            args.name,
            args.role,
            args.department,
            args.group or ["AI-Hub-Users"],
            password,
        )
        print(f"Account saved: {uid}. Previous sessions revoked.")


if __name__ == "__main__":
    main()
