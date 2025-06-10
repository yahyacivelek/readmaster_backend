"""add_system_configurations_table

Revision ID: 0f01c071ef73
Revises: beec79da1f61 # Should be the ID of the previous (initial_tables) migration
Create Date: YYYY-MM-DD HH:MM:SS.SSSSSS # Placeholder, will be filled by Alembic

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # For JSONB type

# revision identifiers, used by Alembic.
revision: str = '0f01c071ef73'
down_revision: Union[str, None] = 'beec79da1f61' # Link to the previous migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands to create SystemConfigurations table ###
    op.execute("""
    CREATE TABLE IF NOT EXISTS "SystemConfigurations" (
        key VARCHAR NOT NULL PRIMARY KEY,
        value JSONB NOT NULL,
        description TEXT,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """)

    # Add trigger for automatic updated_at timestamp
    op.execute("""DROP TRIGGER IF EXISTS set_systemconfigurations_updated_at ON "SystemConfigurations";""")
    op.execute("""
        CREATE TRIGGER set_systemconfigurations_updated_at
        BEFORE UPDATE ON "SystemConfigurations"
        FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
    """)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands to drop SystemConfigurations table ###

    # Drop the trigger first
    op.execute("""
        DROP TRIGGER IF EXISTS set_systemconfigurations_updated_at ON "SystemConfigurations";
    """)

    # Drop the table (using IF EXISTS for robustness)
    op.execute("""DROP TABLE IF EXISTS "SystemConfigurations";""")
    # ### end Alembic commands ###