import sqlalchemy as sa
from alembic import op

revision = "b814cecbec68"
down_revision = "706c352a118c"
branch_labels = None
depends_on = None

# A database created after the convention landed on Base already has the new names:
# env.py passes Base.metadata, and alembic applies its naming_convention to the unnamed
# constraints in the first revision. Only older databases have anything to rename.
RENAMES = (
    ("countries", "countries_code_key", "uq_countries_code"),
    ("countries", "countries_name_key", "uq_countries_name"),
    ("users", "users_email_key", "uq_users_email"),
)


def _rename_if_present(table: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{old}' AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new};
            END IF;
        END $$;
        """  # noqa: S608
    )


def upgrade() -> None:
    for table, old, new in RENAMES:
        _rename_if_present(table, old, new)


def downgrade() -> None:
    for table, old, new in RENAMES:
        _rename_if_present(table, new, old)
