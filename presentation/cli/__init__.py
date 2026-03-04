"""
CLI Interface

Architectural Intent:
- Command-line interface for admin operations
- Health checks, data import/export, migrations
- Salesforce data migration via `nexus migrate` command
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path


def health_check():
    """Check API health."""
    import httpx

    try:
        health_url = os.environ.get("HEALTH_CHECK_URL", "http://localhost:8000")
        response = httpx.get(f"{health_url}/health", timeout=5)
        if response.status_code == 200:
            print("API is healthy")
            return 0
        else:
            print(f"API unhealthy: {response.status_code}")
            return 1
    except Exception as e:
        print(f"API unreachable: {e}")
        return 1


def run_migrate(args):
    """Execute a data migration from an external CRM source."""
    from infrastructure.adapters.salesforce_migration import (
        MigrationConfig,
        SalesforceMigrator,
    )

    # --- Resolve source ---
    source = args.source
    if source != "salesforce":
        print(f"Error: unsupported migration source '{source}'. Supported: salesforce")
        return 1

    # --- Build config from CLI flags + environment variables ---
    export_dir = args.export_dir
    sf_instance_url = args.sf_instance_url or os.environ.get("SF_INSTANCE_URL")
    sf_access_token = os.environ.get("SF_ACCESS_TOKEN")
    sf_client_id = os.environ.get("SF_CLIENT_ID")
    sf_client_secret = os.environ.get("SF_CLIENT_SECRET")
    sf_username = args.sf_username or os.environ.get("SF_USERNAME")
    sf_password = os.environ.get("SF_PASSWORD")

    # Validate that we have either file export or API credentials
    if not export_dir and not sf_instance_url:
        print(
            "Error: provide either --export-dir for file-based import "
            "or --sf-instance-url (plus credentials) for live API import.\n"
            "You can also set SF_INSTANCE_URL, SF_ACCESS_TOKEN, etc. as environment variables."
        )
        return 1

    if export_dir and not Path(export_dir).is_dir():
        print(f"Error: export directory does not exist: {export_dir}")
        return 1

    # Parse object filter
    objects_filter = None
    if args.objects:
        objects_filter = [o.strip() for o in args.objects.split(",")]
        valid_objects = {"Account", "Contact", "Opportunity", "Lead", "Case"}
        invalid = set(objects_filter) - valid_objects
        if invalid:
            print(f"Error: unsupported objects: {', '.join(invalid)}")
            print(f"Valid objects: {', '.join(sorted(valid_objects))}")
            return 1

    config = MigrationConfig(
        sf_instance_url=sf_instance_url,
        sf_access_token=sf_access_token,
        sf_client_id=sf_client_id,
        sf_client_secret=sf_client_secret,
        sf_username=sf_username,
        sf_password=sf_password,
        export_dir=export_dir,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
        objects=objects_filter,
    )

    # --- Configure logging ---
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Run migration ---
    if args.dry_run:
        print("=" * 60)
        print("  DRY RUN MODE - no records will be persisted")
        print("=" * 60)
        print()

    migrator = SalesforceMigrator(config)

    try:
        results = migrator.migrate_all()
    except Exception as exc:
        print(f"\nMigration failed with error: {exc}")
        logging.getLogger(__name__).exception("Migration failed")
        return 1

    # --- Print results ---
    print()
    print(migrator.format_summary())

    # Show errors if any
    total_errors = sum(p.failed for p in results.values())
    if total_errors > 0 and args.verbose:
        print(f"\nDetailed errors ({total_errors} total):")
        for obj_type, progress in results.items():
            for error in progress.errors[:10]:  # Cap at 10 per type
                print(
                    f"  [{obj_type}] SF ID {error.get('sf_id', '?')}: {error.get('error', '?')}"
                )
            if len(progress.errors) > 10:
                print(f"  [{obj_type}] ... and {len(progress.errors) - 10} more")

    # --- Dry-run preview ---
    if args.dry_run and args.preview:
        preview_count = int(args.preview)
        print(f"\nPreview of first {preview_count} transformed records per object:")
        for obj_type in migrator.MIGRATION_ORDER:
            records = migrator.get_migrated_records(obj_type)
            if records:
                print(f"\n--- {obj_type} ({len(records)} total) ---")
                for record in records[:preview_count]:
                    print(json.dumps(record, indent=2, default=str))

    if total_errors > 0:
        print(f"\nMigration completed with {total_errors} errors.")
        return 1

    print("\nMigration completed successfully.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="nexus",
        description="Nexus CRM CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- health ---
    subparsers.add_parser("health", help="Check API health")

    # --- version ---
    subparsers.add_parser("version", help="Show version")

    # --- db-migrate (existing alembic migrations) ---
    db_migrate_parser = subparsers.add_parser(
        "db-migrate", help="Run database schema migrations (Alembic)"
    )
    db_migrate_parser.add_argument("--revision", default="head")

    # --- migrate (data migration from external CRM) ---
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Migrate data from an external CRM into Nexus",
        description=(
            "Import data from Salesforce (or other CRM sources) into Nexus CRM. "
            "Supports both live Salesforce API access and offline CSV/JSON file imports."
        ),
    )
    migrate_parser.add_argument(
        "--source",
        required=True,
        choices=["salesforce"],
        help="Source CRM to migrate from (currently: salesforce)",
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate and transform records without persisting",
    )
    migrate_parser.add_argument(
        "--export-dir",
        metavar="DIR",
        help="Directory containing exported CSV/JSON files (e.g. Account.csv, Contact.json)",
    )
    migrate_parser.add_argument(
        "--objects",
        metavar="LIST",
        help="Comma-separated list of objects to migrate (default: all). "
        "Valid: Account,Contact,Opportunity,Lead,Case",
    )
    migrate_parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of records per persistence batch (default: 500)",
    )
    migrate_parser.add_argument(
        "--output-dir",
        default="./migration_output",
        help="Directory for migration output files (default: ./migration_output)",
    )
    migrate_parser.add_argument(
        "--preview",
        nargs="?",
        const="3",
        metavar="N",
        help="In dry-run mode, show first N transformed records per object (default: 3)",
    )
    migrate_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose/debug logging",
    )

    # Salesforce API connection options
    sf_group = migrate_parser.add_argument_group(
        "Salesforce API options",
        "Credentials are read from environment variables only (SF_INSTANCE_URL, "
        "SF_ACCESS_TOKEN, SF_CLIENT_ID, SF_CLIENT_SECRET, SF_USERNAME, SF_PASSWORD) "
        "to avoid exposing secrets in process listings. "
        "Only --sf-instance-url and --sf-username are accepted as CLI flags.",
    )
    sf_group.add_argument(
        "--sf-instance-url",
        metavar="URL",
        help="Salesforce instance URL (e.g. https://myorg.salesforce.com)",
    )
    sf_group.add_argument(
        "--sf-username", metavar="USER", help="Salesforce username (for password grant)"
    )

    args = parser.parse_args()

    if args.command == "health":
        sys.exit(health_check())
    elif args.command == "version":
        print("Nexus CRM v1.0.0")
    elif args.command == "db-migrate":
        print(f"Running database migrations to {args.revision}...")
        # Alembic migration would run here
    elif args.command == "migrate":
        sys.exit(run_migrate(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
