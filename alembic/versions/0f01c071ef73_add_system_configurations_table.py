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
    op.create_table('SystemConfigurations',
        sa.Column('key', sa.String(), nullable=False, primary_key=True),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp())
    )
    op.create_index(op.f('ix_SystemConfigurations_key'), 'SystemConfigurations', ['key'], unique=False) # Index on PK is often automatic, but explicit for clarity or if ix_ is convention
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands to drop SystemConfigurations table ###
    op.drop_index(op.f('ix_SystemConfigurations_key'), table_name='SystemConfigurations')
    op.drop_table('SystemConfigurations')
    # ### end Alembic commands ###
