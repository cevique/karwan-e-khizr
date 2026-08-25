"""add stops.external_key

Correction pass (see plan.md handoff, "Route topology & data-quality fixes"):
`app/seeding/adapters/stops.py` was matching/deduplicating stops by writing
the CANONICAL DATASET'S SLUG (`transit_data.json`'s `stops[].key`, e.g.
"cda_pims_hospital") into the `stops.name` column, and never writing the
dataset's actual human-readable `stops[].name` (e.g. "PIMS Hospital")
anywhere. Every imported stop's display name was therefore a slug, not a
name - and re-imports never corrected a stop's name even if it changed
upstream, since `_update` didn't touch `name` at all.

This migration adds a dedicated `external_key` column so the importer can
match/dedupe stops by their stable dataset key WITHOUT that key being what
gets shown to a user as the stop's name. `app/seeding/adapters/stops.py`
and `app/seeding/importer.py` are updated in the same pass to use it.

Nullable and only unique where non-null (a plain unique index on a
nullable column already allows any number of NULLs in Postgres) so a stop
that never came from the canonical dataset import (created some other way)
is not required to have one.

Revision ID: a1b2c3d4e5f7
Revises: manual001
Create Date: 2026-08-25 12:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "manual001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("stops", sa.Column("external_key", sa.String(length=255), nullable=True))
    op.create_index(
        op.f("ix_stops_external_key"), "stops", ["external_key"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_stops_external_key"), table_name="stops")
    op.drop_column("stops", "external_key")
