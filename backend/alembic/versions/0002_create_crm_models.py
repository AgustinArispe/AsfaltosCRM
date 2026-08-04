"""Create the initial CRM business model.

Revision ID: 0002_create_crm_models
Revises: 0001_initial_schema
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_create_crm_models"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = postgresql.ENUM(
    "SUPERVISOR",
    "VENDEDOR",
    name="user_role_enum",
    create_type=False,
)
lead_source_enum = postgresql.ENUM(
    "WEB",
    "WHATSAPP",
    name="lead_source_enum",
    create_type=False,
)
opportunity_status_enum = postgresql.ENUM(
    "NUEVA",
    "COTIZADA",
    "NEGOCIACION",
    "GANADA",
    "PERDIDA",
    name="opportunity_status_enum",
    create_type=False,
)
loss_reason_enum = postgresql.ENUM(
    "PRECIO",
    "SIN_RESPUESTA",
    "COMPETENCIA",
    "PROYECTO_CANCELADO",
    "OTRO",
    name="loss_reason_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=False)
    lead_source_enum.create(bind, checkfirst=False)
    opportunity_status_enum.create(bind, checkfirst=False)
    loss_reason_enum.create(bind, checkfirst=False)

    op.create_table(
        "customers",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("province", sa.Text(), nullable=True),
        sa.Column(
            "legendary_historical_override",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_customers_name_not_blank",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_customers_updated_after_created",
        ),
        sa.CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_customers_deleted_after_created",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customers_name_normalized",
        "customers",
        [sa.text("lower(btrim(name))")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_customers_email_normalized",
        "customers",
        [sa.text("lower(btrim(email))")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND email IS NOT NULL"),
    )
    op.create_index(
        "ix_customers_phone_normalized",
        "customers",
        [sa.text("btrim(phone)")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND phone IS NOT NULL"),
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(full_name) <> ''",
            name="ck_users_full_name_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(email) <> ''",
            name="ck_users_email_not_blank",
        ),
        sa.CheckConstraint(
            "btrim(password_hash) <> ''",
            name="ck_users_password_hash_not_blank",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_users_updated_after_created",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_users_email_normalized",
        "users",
        [sa.text("lower(btrim(email))")],
        unique=True,
    )

    op.create_table(
        "products",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name="ck_products_name_not_blank",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_products_updated_after_created",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_products_name_normalized",
        "products",
        [sa.text("lower(btrim(name))")],
        unique=True,
    )

    op.create_table(
        "opportunities",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_user_id", sa.BigInteger(), nullable=True),
        sa.Column("source", lead_source_enum, nullable=False),
        sa.Column(
            "status",
            opportunity_status_enum,
            server_default=sa.text("'NUEVA'"),
            nullable=False,
        ),
        sa.Column("loss_reason", loss_reason_enum, nullable=True),
        sa.Column(
            "current_status_entered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status = 'PERDIDA' AND loss_reason IS NOT NULL) OR "
            "(status <> 'PERDIDA' AND loss_reason IS NULL)",
            name="ck_opportunities_loss_reason_matches_status",
        ),
        sa.CheckConstraint(
            "current_status_entered_at >= created_at",
            name="ck_opportunities_status_entered_after_created",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_opportunities_updated_after_created",
        ),
        sa.CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_opportunities_deleted_after_created",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"],
            ["users.id"],
            name="fk_opportunities_assigned_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_opportunities_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunities_customer_created_at",
        "opportunities",
        ["customer_id", sa.text("created_at DESC")],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_opportunities_status_entered_at",
        "opportunities",
        ["status", "current_status_entered_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_opportunities_assignee_status",
        "opportunities",
        ["assigned_user_id", "status"],
        unique=False,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND assigned_user_id IS NOT NULL"
        ),
    )
    op.create_index(
        "ix_opportunities_source_created_at",
        "opportunities",
        ["source", "created_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_opportunities_legendary_wins",
        "opportunities",
        ["customer_id", "current_status_entered_at"],
        unique=False,
        postgresql_where=sa.text("status = 'GANADA' AND deleted_at IS NULL"),
    )

    op.create_table(
        "opportunity_products",
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(14, 3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity_kg > 0",
            name="ck_opportunity_products_quantity_positive",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_opportunity_products_updated_after_created",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name="fk_opportunity_products_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_opportunity_products_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("opportunity_id", "product_id"),
    )
    op.create_index(
        "ix_opportunity_products_product_opportunity",
        "opportunity_products",
        ["product_id", "opportunity_id"],
        unique=False,
    )

    op.create_table(
        "opportunity_status_history",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("from_status", opportunity_status_enum, nullable=True),
        sa.Column("to_status", opportunity_status_enum, nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("changed_by_user_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "from_status IS NOT NULL OR to_status = 'NUEVA'",
            name="ck_status_history_creation_starts_new",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            name="fk_status_history_changed_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name="fk_status_history_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_status_history_opportunity_changed_at",
        "opportunity_status_history",
        ["opportunity_id", "changed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_status_history_opportunity_changed_at",
        table_name="opportunity_status_history",
    )
    op.drop_table("opportunity_status_history")

    op.drop_index(
        "ix_opportunity_products_product_opportunity",
        table_name="opportunity_products",
    )
    op.drop_table("opportunity_products")

    op.drop_index("ix_opportunities_legendary_wins", table_name="opportunities")
    op.drop_index("ix_opportunities_source_created_at", table_name="opportunities")
    op.drop_index("ix_opportunities_assignee_status", table_name="opportunities")
    op.drop_index("ix_opportunities_status_entered_at", table_name="opportunities")
    op.drop_index("ix_opportunities_customer_created_at", table_name="opportunities")
    op.drop_table("opportunities")

    op.drop_index("uq_products_name_normalized", table_name="products")
    op.drop_table("products")

    op.drop_index("uq_users_email_normalized", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_customers_phone_normalized", table_name="customers")
    op.drop_index("ix_customers_email_normalized", table_name="customers")
    op.drop_index("ix_customers_name_normalized", table_name="customers")
    op.drop_table("customers")

    bind = op.get_bind()
    loss_reason_enum.drop(bind, checkfirst=False)
    opportunity_status_enum.drop(bind, checkfirst=False)
    lead_source_enum.drop(bind, checkfirst=False)
    user_role_enum.drop(bind, checkfirst=False)
