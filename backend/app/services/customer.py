"""客户管理业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "customer"
REQUIRED_FIELDS = ["客户编码", "客户名称", "客户类型"]
STATUS_ORDER = ["待审核", "合作中", "已暂停", "已终止"]
ACTION_RULES = {"审核客户": "合作中", "暂停合作": "已暂停", "终止合作": "已终止"}
NEGATIVE_ACTIONS = []


def _row_status(row: dict[str, Any]) -> str:
    """合作状态同时落在「合作状态」展示字段与「status」流转字段上，筛选取一致口径。"""
    return str(row.get("合作状态") or row.get("status") or "")


class CustomerService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        name: str | None = None,
        customer_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = sorted(store.rows(MODULE), key=lambda row: int(row.get("id", 0)))
        if keyword:
            code = keyword.strip()
            rows = [row for row in rows if code in str(row.get("客户编码", ""))]
        if name:
            customer_name = name.strip()
            rows = [row for row in rows if customer_name in str(row.get("客户名称", ""))]
        if customer_type:
            rows = [row for row in rows if str(row.get("客户类型", "")) == customer_type.strip()]
        if status:
            rows = [row for row in rows if _row_status(row) == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["合作状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"客户档案 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于客户管理可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["合作状态"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"客户档案已{action}"
