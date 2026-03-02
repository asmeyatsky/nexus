"""
CLI Interface

Architectural Intent:
- Command-line interface for admin operations
- Health checks, data import/export, migrations
"""

import argparse
import asyncio
import sys


def health_check():
    """Check API health."""
    import httpx
    try:
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("API is healthy")
            return 0
        else:
            print(f"API unhealthy: {response.status_code}")
            return 1
    except Exception as e:
        print(f"API unreachable: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Nexus CRM CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("health", help="Check API health")
    subparsers.add_parser("version", help="Show version")

    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    migrate_parser.add_argument("--revision", default="head")

    args = parser.parse_args()

    if args.command == "health":
        sys.exit(health_check())
    elif args.command == "version":
        print("Nexus CRM v1.0.0")
    elif args.command == "migrate":
        print(f"Running migrations to {args.revision}...")
        # Alembic migration would run here
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
