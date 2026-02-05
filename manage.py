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
    from datetime import datetime
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
            temp_password = PasswordManager.generate_temp_password()
            user.password_hash = PasswordManager.hash_password(temp_password)
            user.force_password_change = True
            user.password_reset_at = datetime.utcnow()
            db.commit()
            logger.info("Password reset via CLI (temporary password)")
            print(f"\n  ✓  Temporary password set:  {temp_password}")
            print("      User must change password on next login.\n")
        else:
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

                validation = PasswordManager.validate_password_strength(new_password)
                if not validation['valid']:
                    print("  Password does not meet requirements:")
                    for issue in validation['issues']:
                        print(f"    - {issue}")
                    print()
                    continue
                break

            user.password_hash = PasswordManager.hash_password(new_password)
            user.force_password_change = False
            user.password_reset_at = datetime.utcnow()
            db.commit()
            logger.info("Password reset via CLI (new password)")
            print("\n  ✓  Password reset successfully.\n")
    finally:
        db.close()


def main():
    """Main CLI entry point."""

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    # reset-password is self-contained — no Flask app context needed
    if command == 'reset-password':
        reset_password()
        sys.exit(0)

    # All other commands need the Flask app + Flask-Migrate context
    # Imports are lazy so that 'reset-password' above works without flask_migrate
    from flask import Flask
    from flask_migrate import Migrate, upgrade, downgrade, history, current
    from flask_sqlalchemy import SQLAlchemy

    db_path = os.environ.get('DATABASE_PATH', '/tmp/dockermate.db')
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)

    with app.app_context():
        if command == 'db':
            # Flask-Migrate commands
            if len(sys.argv) < 3:
                print("Usage: python manage.py db [init|migrate|upgrade|downgrade|history|current]")
                sys.exit(1)

            subcommand = sys.argv[2]

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

        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)


if __name__ == '__main__':
    main()
