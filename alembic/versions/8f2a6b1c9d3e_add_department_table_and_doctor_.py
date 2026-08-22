"""add department table and doctor/appointment department links

Revision ID: 8f2a6b1c9d3e
Revises: 30ebae28b1e7
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f2a6b1c9d3e'
down_revision: Union[str, None] = '30ebae28b1e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Department",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.add_column("DoctorProfile", sa.Column("departmentId", sa.String(), nullable=True))
    op.create_foreign_key(
        "DoctorProfile_departmentId_fkey",
        "DoctorProfile",
        "Department",
        ["departmentId"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("Appointment", sa.Column("departmentId", sa.String(), nullable=True))
    op.create_foreign_key(
        "Appointment_departmentId_fkey",
        "Appointment",
        "Department",
        ["departmentId"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("Appointment_departmentId_fkey", "Appointment", type_="foreignkey")
    op.drop_column("Appointment", "departmentId")

    op.drop_constraint("DoctorProfile_departmentId_fkey", "DoctorProfile", type_="foreignkey")
    op.drop_column("DoctorProfile", "departmentId")

    op.drop_table("Department")
