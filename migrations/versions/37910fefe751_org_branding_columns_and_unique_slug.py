"""org branding columns and unique slug

Adds the org branding columns (enterprise_teams.slug/logo_url) and the
per-path preview kill-switch (paths.disable_previews) conditionally, so
databases that already received them by hand (the dev box) skip the
ADD COLUMN while untouched databases get them. Org slugs are backfilled
from the organization name, then a unique constraint lands on slug.

Revision ID: 37910fefe751
Revises: afbf65aa806f
Create Date: 2026-10-15 10:11:53.050437

"""
from alembic import op
import sqlalchemy as sa

from slugify import slugify as slugify_func


# revision identifiers, used by Alembic.
revision = '37910fefe751'
down_revision = 'afbf65aa806f'
branch_labels = None
depends_on = None


def _has_column(table, column):
    return any(
        col["name"] == column for col in sa.inspect(op.get_bind()).get_columns(table)
    )


def upgrade():
    if not _has_column("paths", "disable_previews"):
        op.add_column(
            "paths", sa.Column("disable_previews", sa.Boolean(), nullable=True)
        )

    if not _has_column("enterprise_teams", "slug"):
        op.add_column(
            "enterprise_teams", sa.Column("slug", sa.String(220), nullable=True)
        )
    if not _has_column("enterprise_teams", "logo_url"):
        op.add_column(
            "enterprise_teams", sa.Column("logo_url", sa.String(500), nullable=True)
        )

    # backfill slugs from organization names (unique-ified)
    teams = sa.table(
        "enterprise_teams",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
    )
    bind = op.get_bind()
    used = set()
    for rid, name, slug in bind.execute(
        sa.select(teams.c.id, teams.c.name, teams.c.slug)
    ).fetchall():
        if slug:
            used.add(slug)
            continue
        base = slugify_func(name or "") or f"org-{rid}"
        candidate, i = base, 2
        while candidate in used:
            candidate = f"{base}-{i}"
            i += 1
        used.add(candidate)
        bind.execute(teams.update().where(teams.c.id == rid).values(slug=candidate))

    with op.batch_alter_table("enterprise_teams", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_enterprise_teams_slug", ["slug"])


def downgrade():
    with op.batch_alter_table("enterprise_teams", schema=None) as batch_op:
        batch_op.drop_constraint("uq_enterprise_teams_slug", type_="unique")

    if _has_column("enterprise_teams", "logo_url"):
        op.drop_column("enterprise_teams", "logo_url")
    if _has_column("enterprise_teams", "slug"):
        op.drop_column("enterprise_teams", "slug")
    if _has_column("paths", "disable_previews"):
        op.drop_column("paths", "disable_previews")
