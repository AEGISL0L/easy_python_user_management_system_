"""Refactor_db_utcnow

Revision ID: b570529d9974
Revises: 10613a895100
Create Date: 2024-11-04 13:17:38.224600

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b570529d9974'
down_revision = '10613a895100'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('movimiento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fecha_hora_devolucion', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('movimiento', schema=None) as batch_op:
        batch_op.drop_column('fecha_hora_devolucion')

    # ### end Alembic commands ###