"""
Generic tenant-scoped CRUD router. Used for entities whose API is a plain
list/create/get/update/delete against one table (Territory levels,
Category/Sub-Category, Service Charges, Routes, Read Cycles, Meter
Schedules, VEE Rules/Configs/Schedules, Bill Cycles/Templates/Schedules).

Entities with nested data, file uploads, or business-logic side effects
(Rate, Plan, Meter, Consumer, MeterReading, Bill) get hand-written routes
instead -- this factory intentionally stays simple (CLAUDE.md #11).
"""
import datetime
import decimal
from typing import Any, Callable, Optional, Type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.database import get_db
from app.services.audit import record_audit

BeforeWriteHook = Optional[Callable[[Session, str, dict[str, Any]], dict[str, Any]]]


def _jsonable(value: Any) -> Any:
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    return value


def _to_jsonable(obj) -> dict:
    return {
        c.name: _jsonable(getattr(obj, c.name))
        for c in obj.__table__.columns
        if c.name not in ("created_at", "updated_at")
    }


def make_tenant_crud_router(
    *,
    model: Type,
    create_schema: Type[BaseModel],
    update_schema: Type[BaseModel],
    out_schema: Type[BaseModel],
    prefix: str,
    tags: list[str],
    module: str,
    resource: str,
    entity_name: str,
    before_create: BeforeWriteHook = None,
    before_update: BeforeWriteHook = None,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)

    def _get_owned(db: Session, tenant_id: str, item_id: str):
        obj = db.get(model, item_id)
        if obj is None or obj.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity_name} not found")
        return obj

    @router.get("", response_model=list[out_schema])
    def list_items(
        tenant_id: str = Depends(get_tenant_id),
        db: Session = Depends(get_db),
        _=Depends(require_permission(module, resource, "view")),
    ):
        stmt = select(model).where(model.tenant_id == tenant_id)
        return list(db.execute(stmt).scalars().all())

    @router.get("/{item_id}", response_model=out_schema)
    def get_item(
        item_id: str,
        tenant_id: str = Depends(get_tenant_id),
        db: Session = Depends(get_db),
        _=Depends(require_permission(module, resource, "view")),
    ):
        return _get_owned(db, tenant_id, item_id)

    @router.post("", response_model=out_schema, status_code=status.HTTP_201_CREATED)
    def create_item(
        payload: create_schema,
        tenant_id: str = Depends(get_tenant_id),
        db: Session = Depends(get_db),
        current: CurrentUser = Depends(require_permission(module, resource, "create")),
    ):
        data = payload.model_dump()
        if before_create:
            data = before_create(db, tenant_id, data)
        obj = model(tenant_id=tenant_id, **data)
        db.add(obj)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or missing reference, or duplicate value.") from exc
        db.refresh(obj)
        record_audit(
            db, tenant_id=tenant_id, user_id=current.id, module=module, entity=entity_name,
            entity_id=obj.id, action="create", new_value=_to_jsonable(obj),
        )
        return obj

    @router.patch("/{item_id}", response_model=out_schema)
    def update_item(
        item_id: str,
        payload: update_schema,
        tenant_id: str = Depends(get_tenant_id),
        db: Session = Depends(get_db),
        current: CurrentUser = Depends(require_permission(module, resource, "edit")),
    ):
        obj = _get_owned(db, tenant_id, item_id)
        old_value = _to_jsonable(obj)
        data = payload.model_dump(exclude_unset=True)
        if before_update:
            data = before_update(db, tenant_id, data)
        for key, value in data.items():
            setattr(obj, key, value)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or missing reference, or duplicate value.") from exc
        db.refresh(obj)
        record_audit(
            db, tenant_id=tenant_id, user_id=current.id, module=module, entity=entity_name,
            entity_id=obj.id, action="edit", old_value=old_value, new_value=_to_jsonable(obj),
        )
        return obj

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(
        item_id: str,
        tenant_id: str = Depends(get_tenant_id),
        db: Session = Depends(get_db),
        current: CurrentUser = Depends(require_permission(module, resource, "delete")),
    ):
        obj = _get_owned(db, tenant_id, item_id)
        old_value = _to_jsonable(obj)
        db.delete(obj)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete {entity_name}: other records still reference it.",
            ) from exc
        record_audit(
            db, tenant_id=tenant_id, user_id=current.id, module=module, entity=entity_name,
            entity_id=item_id, action="delete", old_value=old_value,
        )
        return None

    return router
