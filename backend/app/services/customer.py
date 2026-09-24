"""客户管理业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "customer"
REQUIRED_FIELDS = ["客户编码", "客户名称", "客户类型"]
STATUS_ORDER = ["待审核", "合作中", "已暂停", "已终止"]
ACTION_RULES = {"审核客户": "合作中", "暂停合作": "已暂停", "终止合作": "已终止"}
NEGATIVE_ACTIONS = []


def _normalized(value: str | None) -> str:
    return str(value or "").strip()


def _contains(row: dict[str, Any], field: str, keyword: str) -> bool:
    return keyword.casefold() in str(row.get(field) or "").casefold()


class CustomerService:
    def list_entries(
        self,
        *,
        customer_code: str | None = None,
        customer_name: str | None = None,
        customer_type: str | None = None,
        type_alias: str | None = None,
        keyword: str | None = None,
        code: str | None = None,
        name: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = sorted(store.rows(MODULE), key=lambda row: int(row.get("id", 0)))
        code_keyword = _normalized(customer_code) or _normalized(code) or _normalized(keyword)
        name_keyword = _normalized(customer_name) or _normalized(name)
        type_keyword = _normalized(customer_type) or _normalized(type_alias)
        status_value = _normalized(status)

        if code_keyword:
            rows = [row for row in rows if _contains(row, "客户编码", code_keyword)]
        if name_keyword:
            rows = [row for row in rows if _contains(row, "客户名称", name_keyword)]
        if type_keyword:
            rows = [row for row in rows if _contains(row, "客户类型", type_keyword)]
        if status_value:
            rows = [row for row in rows if str(row.get("status") or "") == status_value]

        # 客户编码是档案的业务唯一键；异常数据若出现重码，只保留一条，避免分页时重复展示。
        unique_rows: list[dict[str, Any]] = []
        seen_codes: set[str] = set()
        for row in rows:
            customer_code_value = _normalized(str(row.get("客户编码") or ""))
            dedupe_key = customer_code_value or f"id:{row.get('id')}"
            if dedupe_key in seen_codes:
                continue
            seen_codes.add(dedupe_key)
            unique_rows.append(row)

        total = len(unique_rows)
        start = max(page - 1, 0) * size
        return unique_rows[start:start + size], total

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
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"客户档案已{action}"
