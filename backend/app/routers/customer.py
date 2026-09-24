"""客户管理接口：维护客户档案，覆盖审核客户、暂停合作、终止合作等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.customer import CustomerService

router = APIRouter(prefix="/api/customer", tags=["客户管理"])

service = CustomerService()

LIST_FIELDS = ["客户编码", "客户名称", "客户类型", "联系人", "联系电话", "结算方式", "合作状态"]
STATUSES = ["待审核", "合作中", "已暂停", "已终止"]


def _first_param(request: Request, *names: str) -> str | None:
    """兼容既有中文参数、历史 keyword 参数和当前前后端约定参数。"""
    for name in names:
        value = request.query_params.get(name)
        if value and value.strip():
            return value.strip()
    return None


def _list_filters(request: Request) -> dict[str, str | None]:
    return {
        "customer_code": _first_param(request, "customer_code", "customerCode", "code", "客户编码", "keyword"),
        "customer_name": _first_param(request, "customer_name", "customerName", "name", "客户名称"),
        "customer_type": _first_param(request, "customer_type"),
        "type_alias": _first_param(request, "customerType", "type", "客户类型"),
        "status": _first_param(request, "status"),
    }


def _pagination(request: Request) -> tuple[int, int]:
    try:
        page = int(request.query_params.get("page", "1"))
        size = int(request.query_params.get("size", "20"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="页码和每页条数必须是数字") from exc
    if page < 1:
        raise HTTPException(status_code=400, detail="页码必须从 1 开始")
    if size < 1:
        raise HTTPException(status_code=400, detail="每页条数至少为 1")
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    return page, size


@router.get("", response_model=PageResult[dict])
def list_entries(request: Request) -> PageResult[dict]:
    """按客户编码、客户名称、客户类型与状态过滤客户管理列表；没有数据时返回空页，不报错。"""
    page, size = _pagination(request)
    items, total = service.list_entries(page=page, size=size, **_list_filters(request))
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries(request: Request) -> dict[str, Any]:
    """导出客户管理清单：返回当前筛选条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000, **_list_filters(request))
    return {"module": "customer", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条客户档案明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"客户档案 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条客户档案，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="客户档案已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条客户档案执行审核客户、暂停合作、终止合作；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
