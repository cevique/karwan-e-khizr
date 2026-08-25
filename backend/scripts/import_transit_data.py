#!/usr/bin/env python3
"""
Transit Data Import CLI Script

Imports the canonical transit_data.json into the PostgreSQL/PostGIS database.
Usage:
    python scripts/import_transit_data.py
    python scripts/import_transit_data.py --data-file backend/data/transit_data.json
"""
import argparse
import asyncio
import sys
from pathlib import Path

from app.core.database import init_db, close_db, AsyncSessionLocal
from app.seeding.importer import TransitDataImporter, load_transit_data


async def main():
    parser = argparse.ArgumentParser(description="Import transit data from JSON into database")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=Path("backend/data/transit_data.json"),
        help="Path to transit_data.json (default: backend/data/transit_data.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without writing to database",
    )
    args = parser.parse_args()

    if not args.data_file.exists():
        print(f"Error: Data file not found: {args.data_file}")
        sys.exit(1)

    print(f"Loading transit data from {args.data_file}...")
    data = load_transit_data(args.data_file)
    print(f"  Operators: {len(data.get('operators', []))}")
    print(f"  Stops: {len(data.get('stops', []))}")
    print(f"  Routes: {len(data.get('routes', []))}")
    print(f"  Route-Stops: {len(data.get('route_stops', []))}")
    print(f"  Trips: {len(data.get('trips', []))}")

    if args.dry_run:
        print("Dry run complete - no database changes made.")
        return

    print("Initializing database connection...")
    await init_db()

    async with AsyncSessionLocal() as session:
        try:
            print("Starting import...")
            importer = TransitDataImporter(session)
            results = await importer.import_all(data)

            await session.commit()
            print("\nImport completed successfully!")
            print("Results:")
            for entity, count in results.items():
                print(f"  {entity}: {count} records")

        except Exception as e:
            await session.rollback()
            print(f"\nImport failed: {e}")
            raise
        finally:
            await close_db()


if __name__ == "__main__":
    asyncio.run(main())