from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud_factory import make_tenant_crud_router
from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.database import get_db
from app.models.vee import VeeConfig, VeeConfigRule, VeeRule, VeeSchedule
from app.schemas import vee as schemas
from app.services.audit import record_audit

router = APIRouter(tags=["vee"])

router.include_router(
    make_tenant_crud_router(
        model=VeeRule, create_schema=schemas.VeeRuleCreate, update_schema=schemas.VeeRuleUpdate,
        out_schema=schemas.VeeRuleOut, prefix="/vee/rules", tags=["vee"], module="vee", resource="vee", entity_name="VEE Rule",
    )
)


def _config_out(db: Session, config: VeeConfig) -> schemas.VeeConfigOut:
    rule_ids = [r[0] for r in db.execute(select(VeeConfigRule.vee_rule_id).where(VeeConfigRule.vee_config_id == config.id)).all()]
    return schemas.VeeConfigOut(id=config.id, tenant_id=config.tenant_id, name=config.name, utility_service_id=config.utility_service_id, read_type=config.read_type, rule_ids=rule_ids)


@router.get("/vee/configs", response_model=list[schemas.VeeConfigOut], tags=["vee"])
def list_vee_configs(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("vee", "vee", "view"))):
    configs = list(db.execute(select(VeeConfig).where(VeeConfig.tenant_id == tenant_id)).scalars())
    return [_config_out(db, c) for c in configs]


@router.post("/vee/configs", response_model=schemas.VeeConfigOut, status_code=status.HTTP_201_CREATED, tags=["vee"])
def create_vee_config(
    payload: schemas.VeeConfigCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("vee", "vee", "create")),
):
    config = VeeConfig(tenant_id=tenant_id, name=payload.name, utility_service_id=payload.utility_service_id, read_type=payload.read_type)
    db.add(config)
    db.flush()
    for rule_id in payload.rule_ids:
        db.add(VeeConfigRule(vee_config_id=config.id, vee_rule_id=rule_id))
    db.commit()
    db.refresh(config)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="vee", entity="VeeConfig", entity_id=config.id, action="create", new_value=payload.model_dump(mode="json"))
    return _config_out(db, config)


@router.get("/vee/configs/{config_id}", response_model=schemas.VeeConfigOut, tags=["vee"])
def get_vee_config(config_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("vee", "vee", "view"))):
    config = db.get(VeeConfig, config_id)
    if config is None or config.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VEE config not found")
    return _config_out(db, config)


@router.patch("/vee/configs/{config_id}", response_model=schemas.VeeConfigOut, tags=["vee"])
def update_vee_config(
    config_id: str, payload: schemas.VeeConfigUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("vee", "vee", "edit")),
):
    config = db.get(VeeConfig, config_id)
    if config is None or config.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VEE config not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="vee", entity="VeeConfig", entity_id=config.id, action="edit")
    return _config_out(db, config)


router.include_router(
    make_tenant_crud_router(
        model=VeeSchedule, create_schema=schemas.VeeScheduleCreate, update_schema=schemas.VeeScheduleUpdate,
        out_schema=schemas.VeeScheduleOut, prefix="/vee/schedules", tags=["vee"], module="vee", resource="vee", entity_name="VEE Schedule",
    )
)
