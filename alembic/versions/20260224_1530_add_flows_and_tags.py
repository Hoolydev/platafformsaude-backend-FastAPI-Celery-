"""add flows tables, contact tags, conversation flow columns

Revision ID: a1b2c3d4e5f6
Revises: 5c6e487bea2b
Create Date: 2026-02-24 15:30:00.000000-03:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5c6e487bea2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Create flows table
    op.create_table('flows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('configuracoes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flows_id'), 'flows', ['id'], unique=False)
    op.create_index(op.f('ix_flows_tenant_id'), 'flows', ['tenant_id'], unique=False)

    # 2) Create flow_nodes table
    op.create_table('flow_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flow_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=True),
        sa.Column('posicao', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('configuracoes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flow_nodes_id'), 'flow_nodes', ['id'], unique=False)
    op.create_index(op.f('ix_flow_nodes_flow_id'), 'flow_nodes', ['flow_id'], unique=False)

    # 3) Create flow_edges table
    op.create_table('flow_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flow_id', sa.Integer(), nullable=False),
        sa.Column('source_node_id', sa.Integer(), nullable=False),
        sa.Column('target_node_id', sa.Integer(), nullable=False),
        sa.Column('condicao', sa.String(length=255), nullable=True),
        sa.Column('configuracoes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ),
        sa.ForeignKeyConstraint(['source_node_id'], ['flow_nodes.id'], ),
        sa.ForeignKeyConstraint(['target_node_id'], ['flow_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flow_edges_id'), 'flow_edges', ['id'], unique=False)
    op.create_index(op.f('ix_flow_edges_flow_id'), 'flow_edges', ['flow_id'], unique=False)

    # 4) Add tags column to contacts
    op.add_column('contacts',
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # 5) Add flow_id and current_node_id to conversations
    op.add_column('conversations',
        sa.Column('flow_id', sa.Integer(), nullable=True)
    )
    op.add_column('conversations',
        sa.Column('current_node_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key('fk_conversations_flow_id', 'conversations', 'flows', ['flow_id'], ['id'])
    op.create_foreign_key('fk_conversations_current_node_id', 'conversations', 'flow_nodes', ['current_node_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_conversations_current_node_id', 'conversations', type_='foreignkey')
    op.drop_constraint('fk_conversations_flow_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'current_node_id')
    op.drop_column('conversations', 'flow_id')
    op.drop_column('contacts', 'tags')
    op.drop_index(op.f('ix_flow_edges_flow_id'), table_name='flow_edges')
    op.drop_index(op.f('ix_flow_edges_id'), table_name='flow_edges')
    op.drop_table('flow_edges')
    op.drop_index(op.f('ix_flow_nodes_flow_id'), table_name='flow_nodes')
    op.drop_index(op.f('ix_flow_nodes_id'), table_name='flow_nodes')
    op.drop_table('flow_nodes')
    op.drop_index(op.f('ix_flows_tenant_id'), table_name='flows')
    op.drop_index(op.f('ix_flows_id'), table_name='flows')
    op.drop_table('flows')
