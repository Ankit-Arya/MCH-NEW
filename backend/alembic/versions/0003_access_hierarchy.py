"""access hierarchy mappings

Revision ID: 0003_access_hierarchy
Revises: 0002_add_inspection_entries
Create Date: 2026-06-09

This migration is intentionally idempotent because an earlier merge-conflict
migration may have already created user_supervisor_access before Alembic marked
0003_access_hierarchy as applied.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_access_hierarchy"
down_revision = "0002_add_inspection_entries"
branch_labels = None
depends_on = None

TABLE_NAME = "user_supervisor_access"
IX_SUPERVISOR = "ix_user_supervisor_access_supervisor_user_id"
IX_SUBORDINATE = "ix_user_supervisor_access_subordinate_user_id"
UQ_RELATION = "uq_user_supervisor_subordinate_relation"


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return index_name in {idx.get("name") for idx in inspector.get_indexes(table_name)}


def _unique_exists(inspector, table_name: str, constraint_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return constraint_name in {uq.get("name") for uq in inspector.get_unique_constraints(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("supervisor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("subordinate_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("relation_type", sa.String(length=40), nullable=False, server_default="REPORTING"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "supervisor_user_id",
                "subordinate_user_id",
                "relation_type",
                name=UQ_RELATION,
            ),
        )

    # Refresh inspector after possible table creation.
    inspector = sa.inspect(bind)

    if not _unique_exists(inspector, TABLE_NAME, UQ_RELATION):
        op.create_unique_constraint(
            UQ_RELATION,
            TABLE_NAME,
            ["supervisor_user_id", "subordinate_user_id", "relation_type"],
        )

    if not _index_exists(inspector, TABLE_NAME, IX_SUPERVISOR):
        op.create_index(IX_SUPERVISOR, TABLE_NAME, ["supervisor_user_id"])

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, TABLE_NAME, IX_SUBORDINATE):
        op.create_index(IX_SUBORDINATE, TABLE_NAME, ["subordinate_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _index_exists(inspector, TABLE_NAME, IX_SUBORDINATE):
        op.drop_index(IX_SUBORDINATE, table_name=TABLE_NAME)

    inspector = sa.inspect(bind)
    if _index_exists(inspector, TABLE_NAME, IX_SUPERVISOR):
        op.drop_index(IX_SUPERVISOR, table_name=TABLE_NAME)

    inspector = sa.inspect(bind)
    if _table_exists(inspector, TABLE_NAME):
        op.drop_table(TABLE_NAME)
