"""add archive_records table

Revision ID: b3c4d5e6f7a8
Revises: 70c7c6800337
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa

revision    = 'b3c4d5e6f7a8'
down_revision = '70c7c6800337'
branch_labels = None
depends_on    = None


def upgrade():
    op.create_table(
        'archive_records',
        sa.Column('id',                   sa.Integer(),  nullable=False),
        sa.Column('doc_type',             sa.Text(),     nullable=False),
        sa.Column('doc_subtype',          sa.Text(),     nullable=True),
        sa.Column('original_number',      sa.Text(),     nullable=True),
        sa.Column('original_date',        sa.Date(),     nullable=True),
        sa.Column('original_year',        sa.Integer(),  nullable=True),
        sa.Column('original_center',      sa.Text(),     nullable=True),
        sa.Column('original_region',      sa.Text(),     nullable=True),
        sa.Column('person_name',          sa.Text(),     nullable=False),
        sa.Column('person_name_fr',       sa.Text(),     nullable=True),
        sa.Column('person_birth_year',    sa.Integer(),  nullable=True),
        sa.Column('father_name',          sa.Text(),     nullable=True),
        sa.Column('mother_name',          sa.Text(),     nullable=True),
        sa.Column('scan_file',            sa.Text(),     nullable=True),
        sa.Column('scan_quality',         sa.Text(),     nullable=True),
        sa.Column('transcription',        sa.Text(),     nullable=True),
        sa.Column('transcription_status', sa.Text(),     nullable=False,
                  server_default='pending'),
        sa.Column('linked_doc_type',      sa.Text(),     nullable=True),
        sa.Column('linked_record_id',     sa.Integer(),  nullable=True),
        sa.Column('source_type',          sa.Text(),     nullable=False,
                  server_default='paper'),
        sa.Column('register_volume',      sa.Text(),     nullable=True),
        sa.Column('register_page',        sa.Text(),     nullable=True),
        sa.Column('register_entry',       sa.Text(),     nullable=True),
        sa.Column('center_id',            sa.Integer(),  nullable=True),
        sa.Column('digitized_by',         sa.Integer(),  nullable=True),
        sa.Column('verified_by',          sa.Integer(),  nullable=True),
        sa.Column('verified_at',          sa.DateTime(), nullable=True),
        sa.Column('notes',                sa.Text(),     nullable=True),
        sa.Column('is_confidential',      sa.Boolean(),  nullable=True,
                  server_default='0'),
        sa.Column('created_at',           sa.DateTime(), nullable=True),
        sa.Column('updated_at',           sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['center_id'],    ['centers.id']),
        sa.ForeignKeyConstraint(['digitized_by'], ['users.id']),
        sa.ForeignKeyConstraint(['verified_by'],  ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_archive_doc_type',    'archive_records', ['doc_type'])
    op.create_index('ix_archive_person_name', 'archive_records', ['person_name'])
    op.create_index('ix_archive_year',        'archive_records', ['original_year'])
    op.create_index('ix_archive_status',      'archive_records', ['transcription_status'])


def downgrade():
    op.drop_index('ix_archive_status',      'archive_records')
    op.drop_index('ix_archive_year',        'archive_records')
    op.drop_index('ix_archive_person_name', 'archive_records')
    op.drop_index('ix_archive_doc_type',    'archive_records')
    op.drop_table('archive_records')
