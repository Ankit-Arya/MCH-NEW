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


def upgrade() -> None:
    op.create_table(
        "inspection_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("inspection_id", sa.Integer(), sa.ForeignKey("inspections.id"), nullable=False),
        sa.Column("entry_no", sa.String(length=80), nullable=False),
        sa.Column("attribute_id", sa.Integer(), sa.ForeignKey("inspection_attributes.id"), nullable=False),
        sa.Column("sub_area_id", sa.Integer(), sa.ForeignKey("inspection_sub_areas.id"), nullable=False),
        sa.Column("grade_code", sa.String(length=5), nullable=False),
        sa.Column("grade_percentage", sa.Float(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("captured_latitude", sa.Float(), nullable=True),
        sa.Column("captured_longitude", sa.Float(), nullable=True),
        sa.Column("gps_accuracy", sa.Float(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_inspection_entries_inspection_id", "inspection_entries", ["inspection_id"])
    op.create_index("ix_inspection_entries_entry_no", "inspection_entries", ["entry_no"])

    op.add_column("inspection_media", sa.Column("inspection_entry_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_inspection_media_entry",
        "inspection_media",
        "inspection_entries",
        ["inspection_entry_id"],
        ["id"],
    )
    op.create_index("ix_inspection_media_inspection_entry_id", "inspection_media", ["inspection_entry_id"])


def downgrade() -> None:
    op.drop_index("ix_inspection_media_inspection_entry_id", table_name="inspection_media")
    op.drop_constraint("fk_inspection_media_entry", "inspection_media", type_="foreignkey")
    op.drop_column("inspection_media", "inspection_entry_id")
    op.drop_index("ix_inspection_entries_entry_no", table_name="inspection_entries")
    op.drop_index("ix_inspection_entries_inspection_id", table_name="inspection_entries")
    op.drop_table("inspection_entries")
