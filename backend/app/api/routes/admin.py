"""Super Admin platform-level endpoints (CLAUDE.md §6)."""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_superadmin
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantOut, TenantStatusUpdate, TenantUpdate
from app.services.audit import record_audit
from app.services.onboarding import onboard_utility
from app.services.storage import save_upload

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tenants", response_model=list[TenantOut])
def list_tenants(db: Session = Depends(get_db), _=Depends(require_superadmin)) -> list[Tenant]:
    return list(db.execute(select(Tenant)).scalars().all())


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: str, db: Session = Depends(get_db), _=Depends(require_superadmin)) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


class OnboardingResponse(BaseModel):
    tenant: TenantOut
    admin_email: str
    temp_password: str


@router.post("/tenants", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
def onboard_tenant(
    payload: TenantCreate, db: Session = Depends(get_db), current: CurrentUser = Depends(require_superadmin)
) -> OnboardingResponse:
    existing = db.execute(select(User).where(User.email == payload.admin_email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this admin email already exists.")
    result = onboard_utility(db, payload, actor_user_id=current.id)
    return OnboardingResponse(tenant=result.tenant, admin_email=result.admin_user.email, temp_password=result.temp_password)


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: str, payload: TenantUpdate, db: Session = Depends(get_db), current: CurrentUser = Depends(require_superadmin)
) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    old_value = {"name": tenant.name, "status": tenant.status}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, key, value)
    db.commit()
    db.refresh(tenant)
    record_audit(db, tenant_id=tenant.id, user_id=current.id, module="platform", entity="Tenant", entity_id=tenant.id, action="edit", old_value=old_value, new_value={"name": tenant.name})
    return tenant


@router.post("/tenants/{tenant_id}/status", response_model=TenantOut)
def set_tenant_status(
    tenant_id: str, payload: TenantStatusUpdate, db: Session = Depends(get_db), current: CurrentUser = Depends(require_superadmin)
) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    old_status = tenant.status
    tenant.status = payload.status
    tenant.is_active = payload.status == "active"
    db.commit()
    db.refresh(tenant)
    record_audit(db, tenant_id=tenant.id, user_id=current.id, module="platform", entity="Tenant", entity_id=tenant.id, action="edit", old_value={"status": old_status}, new_value={"status": tenant.status})
    return tenant


@router.post("/tenants/{tenant_id}/logo", response_model=TenantOut)
def upload_tenant_logo(
    tenant_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), current: CurrentUser = Depends(require_superadmin)
) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    stored = save_upload(file, sub_dir="logos", allowed_extensions={".jpg", ".jpeg", ".png", ".svg"}, max_mb=2)
    tenant.logo_url = stored.url
    db.commit()
    db.refresh(tenant)
    return tenant


class DashboardOut(BaseModel):
    total_utilities: int
    active_utilities: int
    suspended_utilities: int
    total_consumers: int
    total_meters: int
    bills_generated: int
    failed_jobs: int
    active_users: int


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), _=Depends(require_superadmin)) -> DashboardOut:
    from app.models.consumer import Consumer
    from app.models.meter import Meter
    from app.models.billing import Bill, BillRun

    total = db.execute(select(func.count()).select_from(Tenant)).scalar_one()
    active = db.execute(select(func.count()).select_from(Tenant).where(Tenant.status == "active")).scalar_one()
    suspended = db.execute(select(func.count()).select_from(Tenant).where(Tenant.status == "suspended")).scalar_one()
    consumers = db.execute(select(func.count()).select_from(Consumer)).scalar_one()
    meters = db.execute(select(func.count()).select_from(Meter)).scalar_one()
    bills = db.execute(select(func.count()).select_from(Bill)).scalar_one()
    failed_runs = db.execute(select(func.count()).select_from(BillRun).where(BillRun.status == "failed")).scalar_one()
    active_users = db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True))).scalar_one()

    return DashboardOut(
        total_utilities=total, active_utilities=active, suspended_utilities=suspended,
        total_consumers=consumers, total_meters=meters, bills_generated=bills,
        failed_jobs=failed_runs, active_users=active_users,
    )


class AuditLogOut(BaseModel):
    id: str
    tenant_id: Optional[str]
    user_id: Optional[str]
    module: str
    entity: str
    entity_id: Optional[str]
    action: str
    model_config = {"from_attributes": True}


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_platform_audit_logs(db: Session = Depends(get_db), _=Depends(require_superadmin)) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)
    return list(db.execute(stmt).scalars().all())
