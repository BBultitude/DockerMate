#!/usr/bin/env python3
"""
DockerMate - Database Management CLI
=====================================

DEPRECATED: This script is maintained for compatibility but Alembic is now used directly.

For database migrations, use Alembic commands instead:

    # Generate migration from model changes
    docker compose -f docker-compose.dev.yml exec dockermate alembic revision --autogenerate -m "Description"

    # Apply migrations to database
    docker compose -f docker-compose.dev.yml exec dockermate alembic upgrade head

    # Rollback last migration
    docker compose -f docker-compose.dev.yml exec dockermate alembic downgrade -1

    # Show migration history
    docker compose -f docker-compose.dev.yml exec dockermate alembic history

    # Show current migration version
    docker compose -f docker-compose.dev.yml exec dockermate alembic current

Workflow for Schema Changes:
    1. Modify your model classes in backend/models/
    2. Generate migration: alembic revision --autogenerate -m "Add new_field to User"
    3. Review generated migration in migrations/versions/
    4. Apply migration: alembic upgrade head
    5. Commit migration file to git

Educational Notes:
    - Migrations track database schema changes over time
    - Always review auto-generated migrations before applying
    - Migrations run automatically on container startup
    - Commit migration files to version control
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


def _prompt_new_password(password_manager_cls, getpass):
    """Prompt user for a new password interactively, re-prompting on failures."""
    print("\n  Enter a new password (min 12 chars, upper + lower + digit).\n")
    while True:
        new_password = getpass.getpass("  New password:      ")
        if not new_password:
            print("  Password cannot be empty.\n")
            continue
        confirm = getpass.getpass("  Confirm password:  ")
        if new_password != confirm:
            print("  Passwords do not match. Try again.\n")
            continue
        validation = password_manager_cls.validate_password_strength(new_password)
        if not validation['valid']:
            print("  Password does not meet requirements:")
            for issue in validation['issues']:
                print(f"    - {issue}")
            print()
            continue
        return new_password


def _apply_temp_password(user, db, password_manager_cls, logger, datetime, timezone):
    """Set a generated temporary password and force change on next login."""
    temp_password = password_manager_cls.generate_temp_password()
    user.password_hash = password_manager_cls.hash_password(temp_password)
    user.force_password_change = True
    user.password_reset_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Password reset via CLI (temporary password)")
    print(f"\n  ✓  Temporary password set:  {temp_password}")
    print("      User must change password on next login.\n")


def reset_password():
    """
    Reset the admin password via CLI.

    Security: CLI-only — there is no web endpoint for password reset.
    This prevents brute-force or unauthenticated reset attacks.

    Usage:
        python manage.py reset-password          # interactive: type new password
        python manage.py reset-password --temp   # generate a temporary password
                                                 # (user must change on next login)
    """
    import getpass
    import logging
    from datetime import datetime, timezone
    from backend.models.database import SessionLocal, init_db
    from backend.models.user import User
    from backend.auth.password_manager import PasswordManager

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    use_temp = '--temp' in sys.argv

    print("=" * 60)
    print("  DockerMate — Password Reset (CLI)")
    print("=" * 60)

    init_db()
    db = SessionLocal()
    try:
        user = User.get_admin(db)
        if not user:
            print("\n  ❌  No user found — initial setup has not been completed.")
            sys.exit(1)

        if use_temp:
            _apply_temp_password(user, db, PasswordManager, logger, datetime, timezone)
        else:
            new_password = _prompt_new_password(PasswordManager, getpass)
            user.password_hash = PasswordManager.hash_password(new_password)
            user.force_password_change = False
            user.password_reset_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("Password reset via CLI (new password)")
            print("\n  ✓  Password reset successfully.\n")
    finally:
        db.close()


def _handle_db_subcommand(subcommand: str) -> None:
    """Execute a Flask-Migrate db subcommand (must be called inside app context)."""
    from flask_migrate import upgrade, downgrade, history, current

    if subcommand == 'init':
        print("Initializing migrations...")
        from flask_migrate import init
        init()
        print("✓ Migrations initialized in 'migrations/' directory")
    elif subcommand == 'migrate':
        message = sys.argv[3] if len(sys.argv) > 3 else "Auto-generated migration"
        print(f"Generating migration: {message}")
        from flask_migrate import migrate as run_migrate
        run_migrate(message=message)
        print("✓ Migration generated. Review it in migrations/versions/")
    elif subcommand == 'upgrade':
        revision = sys.argv[3] if len(sys.argv) > 3 else 'head'
        print(f"Upgrading database to {revision}...")
        upgrade(revision=revision)
        print("✓ Database upgraded successfully")
    elif subcommand == 'downgrade':
        revision = sys.argv[3] if len(sys.argv) > 3 else '-1'
        print(f"Downgrading database to {revision}...")
        downgrade(revision=revision)
        print("✓ Database downgraded successfully")
    elif subcommand == 'history':
        print("Migration history:")
        history()
    elif subcommand == 'current':
        print("Current migration version:")
        current()
    else:
        print(f"Unknown subcommand: {subcommand}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == 'reset-password':
        reset_password()
        sys.exit(0)

    from flask import Flask
    from flask_migrate import Migrate
    from flask_sqlalchemy import SQLAlchemy

    db_path = os.environ.get('DATABASE_PATH', '/tmp/dockermate.db')  # NOSONAR
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    _ = Migrate(app, db)

    with app.app_context():
        if command == 'db':
            if len(sys.argv) < 3:
                print("Usage: python manage.py db [init|migrate|upgrade|downgrade|history|current]")
                sys.exit(1)
            _handle_db_subcommand(sys.argv[2])
        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)


if __name__ == '__main__':
    main()
