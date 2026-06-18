# """add inspection entries for selected-area inspection flow

# Revision ID: 0002_add_inspection_entries
# Revises: 0001_initial_schema
# Create Date: 2026-06-02 00:00:00
# """
# from typing import Sequence, Union
# from alembic import op
# import sqlalchemy as sa

# revision: str = "0002_add_inspection_entries"
# down_revision: Union[str, None] = "0001_initial_schema"
# branch_labels: Union[str, Sequence[str], None] = None
# depends_on: Union[str, Sequence[str], None] = None


# def upgrade() -> None:
#     op.create_table(
#         "inspection_entries",
#         sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
#         sa.Column("inspection_id", sa.Integer(), sa.ForeignKey("inspections.id"), nullable=False),
#         sa.Column("entry_no", sa.String(length=80), nullable=False),
#         sa.Column("attribute_id", sa.Integer(), sa.ForeignKey("inspection_attributes.id"), nullable=False),
#         sa.Column("sub_area_id", sa.Integer(), sa.ForeignKey("inspection_sub_areas.id"), nullable=False),
#         sa.Column("grade_code", sa.String(length=5), nullable=False),
#         sa.Column("grade_percentage", sa.Float(), nullable=False),
#         sa.Column("remarks", sa.Text(), nullable=True),
#         sa.Column("captured_latitude", sa.Float(), nullable=True),
#         sa.Column("captured_longitude", sa.Float(), nullable=True),
#         sa.Column("gps_accuracy", sa.Float(), nullable=True),
#         sa.Column("captured_at", sa.DateTime(), nullable=True),
#         sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
#         sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
#         sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
#         sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
#     )
#     op.create_index("ix_inspection_entries_inspection_id", "inspection_entries", ["inspection_id"])
#     op.create_index("ix_inspection_entries_entry_no", "inspection_entries", ["entry_no"])

#     op.add_column("inspection_media", sa.Column("inspection_entry_id", sa.Integer(), nullable=True))
#     op.create_foreign_key(
#         "fk_inspection_media_entry",
#         "inspection_media",
#         "inspection_entries",
#         ["inspection_entry_id"],
#         ["id"],
#     )
#     op.create_index("ix_inspection_media_inspection_entry_id", "inspection_media", ["inspection_entry_id"])


# def downgrade() -> None:
#     op.drop_index("ix_inspection_media_inspection_entry_id", table_name="inspection_media")
#     op.drop_constraint("fk_inspection_media_entry", "inspection_media", type_="foreignkey")
#     op.drop_column("inspection_media", "inspection_entry_id")
#     op.drop_index("ix_inspection_entries_entry_no", table_name="inspection_entries")
#     op.drop_index("ix_inspection_entries_inspection_id", table_name="inspection_entries")
#     op.drop_table("inspection_entries")




"""add inspection entries for selected-area inspection flow

Revision ID: 0002_add_inspection_entries
Revises: 0001_initial_schema
Create Date: 2026-06-02 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_inspection_entries"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_INSPECTION_ENTRIES = "inspection_entries"
TABLE_INSPECTION_MEDIA = "inspection_media"

IX_ENTRIES_INSPECTION_ID = "ix_inspection_entries_inspection_id"
IX_ENTRIES_ENTRY_NO = "ix_inspection_entries_entry_no"
IX_MEDIA_ENTRY_ID = "ix_inspection_media_inspection_entry_id"

FK_MEDIA_ENTRY = "fk_inspection_media_entry"


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False

    return column_name in {
        column.get("name")
        for column in inspector.get_columns(table_name)
    }


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False

    return index_name in {
        index.get("name")
        for index in inspector.get_indexes(table_name)
    }


def _fk_exists(inspector, table_name: str, fk_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False

    return fk_name in {
        fk.get("name")
        for fk in inspector.get_foreign_keys(table_name)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Create inspection_entries only if missing.
    if not _table_exists(inspector, TABLE_INSPECTION_ENTRIES):
        op.create_table(
            TABLE_INSPECTION_ENTRIES,
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "inspection_id",
                sa.Integer(),
                sa.ForeignKey("inspections.id"),
                nullable=False,
            ),
            sa.Column("entry_no", sa.String(length=80), nullable=False),
            sa.Column(
                "attribute_id",
                sa.Integer(),
                sa.ForeignKey("inspection_attributes.id"),
                nullable=False,
            ),
            sa.Column(
                "sub_area_id",
                sa.Integer(),
                sa.ForeignKey("inspection_sub_areas.id"),
                nullable=False,
            ),
            sa.Column("grade_code", sa.String(length=5), nullable=False),
            sa.Column("grade_percentage", sa.Float(), nullable=False),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("captured_latitude", sa.Float(), nullable=True),
            sa.Column("captured_longitude", sa.Float(), nullable=True),
            sa.Column("gps_accuracy", sa.Float(), nullable=True),
            sa.Column("captured_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_by",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    # Refresh inspector after possible table creation.
    inspector = sa.inspect(bind)

    # 2. Create indexes on inspection_entries only if missing.
    if not _index_exists(
        inspector,
        TABLE_INSPECTION_ENTRIES,
        IX_ENTRIES_INSPECTION_ID,
    ):
        op.create_index(
            IX_ENTRIES_INSPECTION_ID,
            TABLE_INSPECTION_ENTRIES,
            ["inspection_id"],
        )

    inspector = sa.inspect(bind)

    if not _index_exists(
        inspector,
        TABLE_INSPECTION_ENTRIES,
        IX_ENTRIES_ENTRY_NO,
    ):
        op.create_index(
            IX_ENTRIES_ENTRY_NO,
            TABLE_INSPECTION_ENTRIES,
            ["entry_no"],
        )

    # Refresh inspector before checking inspection_media.
    inspector = sa.inspect(bind)

    # 3. Add inspection_media.inspection_entry_id only if missing.
    if not _column_exists(
        inspector,
        TABLE_INSPECTION_MEDIA,
        "inspection_entry_id",
    ):
        op.add_column(
            TABLE_INSPECTION_MEDIA,
            sa.Column("inspection_entry_id", sa.Integer(), nullable=True),
        )

    inspector = sa.inspect(bind)

    # 4. Add FK only if missing.
    if not _fk_exists(
        inspector,
        TABLE_INSPECTION_MEDIA,
        FK_MEDIA_ENTRY,
    ):
        op.create_foreign_key(
            FK_MEDIA_ENTRY,
            TABLE_INSPECTION_MEDIA,
            TABLE_INSPECTION_ENTRIES,
            ["inspection_entry_id"],
            ["id"],
        )

    inspector = sa.inspect(bind)

    # 5. Add index only if missing.
    if not _index_exists(
        inspector,
        TABLE_INSPECTION_MEDIA,
        IX_MEDIA_ENTRY_ID,
    ):
        op.create_index(
            IX_MEDIA_ENTRY_ID,
            TABLE_INSPECTION_MEDIA,
            ["inspection_entry_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _index_exists(
        inspector,
        TABLE_INSPECTION_MEDIA,
        IX_MEDIA_ENTRY_ID,
    ):
        op.drop_index(
            IX_MEDIA_ENTRY_ID,
            table_name=TABLE_INSPECTION_MEDIA,
        )

    inspector = sa.inspect(bind)

    if _fk_exists(
        inspector,
        TABLE_INSPECTION_MEDIA,
        FK_MEDIA_ENTRY,
    ):
        op.drop_constraint(
            FK_MEDIA_ENTRY,
            TABLE_INSPECTION_MEDIA,
            type_="foreignkey",
        )

    inspector = sa.inspect(bind)

    if _column_exists(
        inspector,
        TABLE_INSPECTION_MEDIA,
        "inspection_entry_id",
    ):
        op.drop_column(
            TABLE_INSPECTION_MEDIA,
            "inspection_entry_id",
        )

    inspector = sa.inspect(bind)

    if _index_exists(
        inspector,
        TABLE_INSPECTION_ENTRIES,
        IX_ENTRIES_ENTRY_NO,
    ):
        op.drop_index(
            IX_ENTRIES_ENTRY_NO,
            table_name=TABLE_INSPECTION_ENTRIES,
        )

    inspector = sa.inspect(bind)

    if _index_exists(
        inspector,
        TABLE_INSPECTION_ENTRIES,
        IX_ENTRIES_INSPECTION_ID,
    ):
        op.drop_index(
            IX_ENTRIES_INSPECTION_ID,
            table_name=TABLE_INSPECTION_ENTRIES,
        )

    inspector = sa.inspect(bind)

    if _table_exists(inspector, TABLE_INSPECTION_ENTRIES):
        op.drop_table(TABLE_INSPECTION_ENTRIES)