"""Workbook §7 'Utility Service': global catalogue + per-tenant on/off
toggle. Never hard-code service names in business logic -- everything
joins through utility_services.id."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.database import get_db
from app.models.service import TenantService, UtilityService
from app.schemas.service import TenantServiceOut, TenantServiceToggle, UtilityServiceOut

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/catalogue", response_model=list[UtilityServiceOut])
def list_catalogue(db: Session = Depends(get_db)):
    return list(db.execute(select(UtilityService)).scalars().all())


@router.get("/tenant", response_model=list[TenantServiceOut])
def list_tenant_services(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    _=Depends(require_permission("tenant", "tenant", "view")),
):
    catalogue = list(db.execute(select(UtilityService)).scalars().all())
    enabled = {
        ts.utility_service_id: ts.is_enabled
        for ts in db.execute(select(TenantService).where(TenantService.tenant_id == tenant_id)).scalars()
    }
    return [
        TenantServiceOut(utility_service_id=svc.id, name=svc.name, is_enabled=enabled.get(svc.id, False))
        for svc in catalogue
    ]


@router.put("/tenant", response_model=TenantServiceOut)
def toggle_tenant_service(
    payload: TenantServiceToggle,
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("tenant", "tenant", "edit")),
):
    svc = db.get(UtilityService, payload.utility_service_id)
    existing = db.execute(
        select(TenantService).where(
            TenantService.tenant_id == tenant_id, TenantService.utility_service_id == payload.utility_service_id
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = TenantService(tenant_id=tenant_id, utility_service_id=payload.utility_service_id, is_enabled=payload.is_enabled)
        db.add(existing)
    else:
        existing.is_enabled = payload.is_enabled
    db.commit()
    return TenantServiceOut(utility_service_id=payload.utility_service_id, name=svc.name if svc else "", is_enabled=payload.is_enabled)
