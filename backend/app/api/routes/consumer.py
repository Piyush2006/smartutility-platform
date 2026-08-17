import secrets

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.models.account import Plan
from app.models.consumer import Consumer
from app.models.meter import Meter
from app.models.rbac import Role, UserRole
from app.models.territory import Premise
from app.models.user import User
from app.schemas.consumer import ConsumerCreate, ConsumerOut, ConsumerUpdate
from app.services.audit import record_audit
from app.services.storage import save_upload

router = APIRouter(prefix="/consumers", tags=["consumer"])


class IdDocumentOut(BaseModel):
    url: str


@router.post("/id-document", response_model=IdDocumentOut)
def upload_id_document(
    file: UploadFile = File(...), _tenant_id: str = Depends(get_tenant_id),
    __=Depends(require_permission("consumer", "consumer", "create")),
):
    stored = save_upload(file, sub_dir="consumer-ids", allowed_extensions={".pdf", ".jpg", ".jpeg", ".png"}, max_mb=5)
    return IdDocumentOut(url=stored.url)


@router.get("", response_model=list[ConsumerOut])
def list_consumers(
    tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("consumer", "consumer", "view")),
):
    stmt = select(Consumer).where(Consumer.tenant_id == tenant_id)
    # Property Manager: scoped to only their assigned consumers (CLAUDE.md §5).
    role_names = {r.name for r in db.execute(select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current.id)).scalars()}
    if role_names == {"Property Manager"}:
        stmt = stmt.where(Consumer.property_manager_user_id == current.id)
    return list(db.execute(stmt).scalars())


@router.get("/{consumer_id}", response_model=ConsumerOut)
def get_consumer(consumer_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("consumer", "consumer", "view"))):
    consumer = db.get(Consumer, consumer_id)
    if consumer is None or consumer.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consumer not found")
    return consumer


class ConsumerCreateResponse(BaseModel):
    consumer: ConsumerOut
    portal_email: str
    portal_temp_password: str


@router.post("", response_model=ConsumerCreateResponse, status_code=status.HTTP_201_CREATED)
def create_consumer(
    payload: ConsumerCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("consumer", "consumer", "create")),
):
    premise = db.get(Premise, payload.premise_id)
    if premise is None or premise.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter premise name or number.")
    plan = db.get(Plan, payload.plan_id)
    if plan is None or plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a valid plan.")
    meter = db.get(Meter, payload.meter_id)
    if meter is None or meter.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a meter.")
    if meter.is_assigned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meter is already assigned to another consumer.")
    if db.execute(select(User).where(User.email == payload.email_address)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter valid email.")

    consumer_role = db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == "Consumer")).scalar_one_or_none()
    if consumer_role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant is missing the Consumer role -- re-run onboarding.")

    temp_password = secrets.token_urlsafe(9)
    portal_user = User(tenant_id=tenant_id, email=payload.email_address, full_name=payload.full_name, password_hash=hash_password(temp_password))
    db.add(portal_user)
    db.flush()
    db.add(UserRole(user_id=portal_user.id, role_id=consumer_role.id))

    consumer = Consumer(tenant_id=tenant_id, user_id=portal_user.id, **payload.model_dump())
    db.add(consumer)
    meter.is_assigned = True
    db.commit()
    db.refresh(consumer)

    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="consumer", entity="Consumer", entity_id=consumer.id, action="create", new_value={"full_name": consumer.full_name})
    return ConsumerCreateResponse(consumer=consumer, portal_email=portal_user.email, portal_temp_password=temp_password)


@router.patch("/{consumer_id}", response_model=ConsumerOut)
def update_consumer(
    consumer_id: str, payload: ConsumerUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("consumer", "consumer", "edit")),
):
    consumer = db.get(Consumer, consumer_id)
    if consumer is None or consumer.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consumer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(consumer, key, value)
    db.commit()
    db.refresh(consumer)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="consumer", entity="Consumer", entity_id=consumer.id, action="edit")
    return consumer
