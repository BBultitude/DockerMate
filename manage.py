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
from flask import Flask
from flask_migrate import Migrate, init as migrate_init, migrate as migrate_migrate, upgrade, downgrade, history, current
from flask_sqlalchemy import SQLAlchemy

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.models.database import db, init_db
from backend.models.user import User
from backend.models.container import Container
from backend.models.system import HostConfig


def create_app():
    """Create Flask app for migration management."""
    app = Flask(__name__)

    # Database configuration
    db_path = os.environ.get('DATABASE_PATH', '/tmp/dockermate.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    db.init_app(app)

    return app


def main():
    """Main CLI entry point."""
    app = create_app()
    migrate = Migrate(app, db)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

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
                from flask_migrate import migrate
                migrate(message=message)
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
