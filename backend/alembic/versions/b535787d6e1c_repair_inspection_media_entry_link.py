"""repair inspection media entry link

Revision ID: 0004_repair_inspection_media_entry_link
Revises: 0003_access_hierarchy
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_repair_inspection_media_entry_link"
down_revision = "0003_access_hierarchy"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _fk_exists(inspector, table_name: str, fk_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return fk_name in {fk.get("name") for fk in inspector.get_foreign_keys(table_name)}


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return index_name in {idx.get("name") for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "inspection_media", "inspection_entry_id"):
        op.add_column(
            "inspection_media",
            sa.Column("inspection_entry_id", sa.Integer(), nullable=True),
        )

    inspector = sa.inspect(bind)

    if not _fk_exists(inspector, "inspection_media", "fk_inspection_media_entry"):
        op.create_foreign_key(
            "fk_inspection_media_entry",
            "inspection_media",
            "inspection_entries",
            ["inspection_entry_id"],
            ["id"],
        )

    inspector = sa.inspect(bind)

    if not _index_exists(
        inspector,
        "inspection_media",
        "ix_inspection_media_inspection_entry_id",
    ):
        op.create_index(
            "ix_inspection_media_inspection_entry_id",
            "inspection_media",
            ["inspection_entry_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _index_exists(
        inspector,
        "inspection_media",
        "ix_inspection_media_inspection_entry_id",
    ):
        op.drop_index(
            "ix_inspection_media_inspection_entry_id",
            table_name="inspection_media",
        )

    inspector = sa.inspect(bind)

    if _fk_exists(inspector, "inspection_media", "fk_inspection_media_entry"):
        op.drop_constraint(
            "fk_inspection_media_entry",
            "inspection_media",
            type_="foreignkey",
        )

    inspector = sa.inspect(bind)

    if _column_exists(inspector, "inspection_media", "inspection_entry_id"):
        op.drop_column("inspection_media", "inspection_entry_id")