"""restore unique constraints for reservation and approval tables

Revision ID: b8d4f2a1c9e6
Revises: c4371dcc7166
Create Date: 2026-08-14

修复 2026-08-14 审查发现的约束丢失问题：
- classroom_reservation 唯一索引 uk_room_time（教室预约并发竞态防护）
- approval_record 唯一索引 uk_leave_level（请假审批幂等防护）
升级前自动去重（保留 id 最新记录），避免存量脏数据导致建索引失败。
"""
from typing import Sequence, Union

import logging

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8d4f2a1c9e6'
down_revision: Union[str, Sequence[str], None] = 'c4371dcc7166'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def _dedup_keep_newest(bind, table: str, cols: list[str]) -> int:
    """删除重复行，保留每个唯一键下 id 最大（最新）的一条。返回删除行数。"""
    rows = bind.execute(sa.text(f"SELECT id, {', '.join(cols)} FROM `{table}`")).fetchall()
    if not rows:
        return 0
    kept: dict = {}
    for row in rows:
        key = tuple(row[c] for c in cols)
        if key not in kept or row["id"] > kept[key]:
            kept[key] = row["id"]
    keep_ids = set(kept.values())
    dup_ids = [row["id"] for row in rows if row["id"] not in keep_ids]
    if dup_ids:
        id_list = ", ".join(str(i) for i in dup_ids)
        bind.execute(sa.text(f"DELETE FROM `{table}` WHERE id IN ({id_list})"))
    return len(dup_ids)


def upgrade() -> None:
    """去重后重建唯一索引（保留最新记录）。"""
    bind = op.get_bind()
    n_reserve = _dedup_keep_newest(
        bind, "classroom_reservation",
        ["classroom_id", "week", "day_of_week", "period"],
    )
    n_approval = _dedup_keep_newest(bind, "approval_record", ["leave_id", "level"])
    logger.info("dedup removed %d reservation rows and %d approval rows", n_reserve, n_approval)
    op.create_index(
        "uk_room_time", "classroom_reservation",
        ["classroom_id", "week", "day_of_week", "period"], unique=True,
    )
    op.create_index(
        "uk_leave_level", "approval_record",
        ["leave_id", "level"], unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uk_room_time", table_name="classroom_reservation")
    op.drop_index("uk_leave_level", table_name="approval_record")
