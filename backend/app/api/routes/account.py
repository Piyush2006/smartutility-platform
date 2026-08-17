from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud_factory import make_tenant_crud_router
from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.database import get_db
from app.models.account import (
    Category,
    Plan,
    PlanComponent,
    Rate,
    RateTier,
    ServiceCharge,
    SubCategory,
    TouRate,
)
from app.schemas import account as schemas
from app.services.audit import record_audit

router = APIRouter(tags=["account"])

router.include_router(
    make_tenant_crud_router(
        model=Category, create_schema=schemas.CategoryCreate, update_schema=schemas.CategoryUpdate,
        out_schema=schemas.CategoryOut, prefix="/categories", tags=["account"], module="account",
        resource="account", entity_name="Category",
    )
)
router.include_router(
    make_tenant_crud_router(
        model=SubCategory, create_schema=schemas.SubCategoryCreate, update_schema=schemas.SubCategoryUpdate,
        out_schema=schemas.SubCategoryOut, prefix="/sub-categories", tags=["account"], module="account",
        resource="account", entity_name="Sub-Category",
    )
)
router.include_router(
    make_tenant_crud_router(
        model=ServiceCharge, create_schema=schemas.ServiceChargeCreate, update_schema=schemas.ServiceChargeUpdate,
        out_schema=schemas.ServiceChargeOut, prefix="/service-charges", tags=["account"], module="account",
        resource="account", entity_name="Service Charge",
    )
)


# ---- Rate (nested tiers / TOU rows) ---------------------------------------

def _rate_out(db: Session, rate: Rate) -> schemas.RateOut:
    tiers = list(db.execute(select(RateTier).where(RateTier.rate_id == rate.id)).scalars())
    tou = list(db.execute(select(TouRate).where(TouRate.rate_id == rate.id)).scalars())
    return schemas.RateOut(
        id=rate.id, tenant_id=rate.tenant_id, name=rate.name, rate_type=rate.rate_type, rate=rate.rate,
        basis=rate.basis, tiers=[schemas.RateTierOut.model_validate(t) for t in tiers],
        tou_rates=[schemas.TouRateOut.model_validate(t) for t in tou],
    )


@router.get("/rates", response_model=list[schemas.RateOut], tags=["account"])
def list_rates(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("account", "account", "view"))):
    rates = list(db.execute(select(Rate).where(Rate.tenant_id == tenant_id)).scalars())
    return [_rate_out(db, r) for r in rates]


@router.get("/rates/{rate_id}", response_model=schemas.RateOut, tags=["account"])
def get_rate(rate_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("account", "account", "view"))):
    rate = db.get(Rate, rate_id)
    if rate is None or rate.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found")
    return _rate_out(db, rate)


@router.post("/rates", response_model=schemas.RateOut, status_code=status.HTTP_201_CREATED, tags=["account"])
def create_rate(
    payload: schemas.RateCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("account", "account", "create")),
):
    rate = Rate(tenant_id=tenant_id, name=payload.name, rate_type=payload.rate_type, rate=payload.rate, basis=payload.basis)
    db.add(rate)
    db.flush()

    if payload.tiers:
        for tier in payload.tiers:
            db.add(RateTier(tenant_id=tenant_id, rate_id=rate.id, tier_from=tier.tier_from, tier_to=tier.tier_to, price=tier.price))
    if payload.tou_rates:
        for window in payload.tou_rates:
            db.add(TouRate(tenant_id=tenant_id, rate_id=rate.id, start_time=window.start_time, end_time=window.end_time, price=window.price))

    db.commit()
    db.refresh(rate)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="account", entity="Rate", entity_id=rate.id, action="create", new_value=payload.model_dump(mode="json"))
    return _rate_out(db, rate)


@router.patch("/rates/{rate_id}", response_model=schemas.RateOut, tags=["account"])
def update_rate(
    rate_id: str, payload: schemas.RateUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("account", "account", "edit")),
):
    """Only name and (for fixed/per_unit_area) the flat rate can be edited
    here -- changing rate_type/basis would invalidate the tiers/TOU rows
    already attached, so that requires deleting and recreating the rate."""
    rate = db.get(Rate, rate_id)
    if rate is None or rate.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rate, key, value)
    db.commit()
    db.refresh(rate)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="account", entity="Rate", entity_id=rate.id, action="edit")
    return _rate_out(db, rate)


@router.delete("/rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["account"])
def delete_rate(rate_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), current: CurrentUser = Depends(require_permission("account", "account", "delete"))):
    rate = db.get(Rate, rate_id)
    if rate is None or rate.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found")
    for tier in db.execute(select(RateTier).where(RateTier.rate_id == rate.id)).scalars():
        db.delete(tier)
    for window in db.execute(select(TouRate).where(TouRate.rate_id == rate.id)).scalars():
        db.delete(window)
    db.delete(rate)
    db.commit()
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="account", entity="Rate", entity_id=rate_id, action="delete")
    return None


# ---- Plan (nested components) ---------------------------------------------

def _plan_out(db: Session, plan: Plan) -> schemas.PlanOut:
    components = list(db.execute(select(PlanComponent).where(PlanComponent.plan_id == plan.id)).scalars())
    return schemas.PlanOut(
        id=plan.id, tenant_id=plan.tenant_id, name=plan.name, category_id=plan.category_id,
        sub_category_id=plan.sub_category_id, tax_percent=plan.tax_percent, billing_frequency=plan.billing_frequency,
        is_active=plan.is_active, components=[schemas.PlanComponentOut.model_validate(c) for c in components],
    )


@router.get("/plans", response_model=list[schemas.PlanOut], tags=["account"])
def list_plans(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("account", "account", "view"))):
    plans = list(db.execute(select(Plan).where(Plan.tenant_id == tenant_id)).scalars())
    return [_plan_out(db, p) for p in plans]


@router.get("/plans/{plan_id}", response_model=schemas.PlanOut, tags=["account"])
def get_plan(plan_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("account", "account", "view"))):
    plan = db.get(Plan, plan_id)
    if plan is None or plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return _plan_out(db, plan)


@router.post("/plans", response_model=schemas.PlanOut, status_code=status.HTTP_201_CREATED, tags=["account"])
def create_plan(
    payload: schemas.PlanCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("account", "account", "create")),
):
    plan = Plan(
        tenant_id=tenant_id, name=payload.name, category_id=payload.category_id, sub_category_id=payload.sub_category_id,
        tax_percent=payload.tax_percent, billing_frequency=payload.billing_frequency,
    )
    db.add(plan)
    db.flush()
    for comp in payload.components:
        db.add(PlanComponent(tenant_id=tenant_id, plan_id=plan.id, utility_service_id=comp.utility_service_id, rate_id=comp.rate_id))
    db.commit()
    db.refresh(plan)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="account", entity="Plan", entity_id=plan.id, action="create", new_value=payload.model_dump(mode="json"))
    return _plan_out(db, plan)


@router.patch("/plans/{plan_id}", response_model=schemas.PlanOut, tags=["account"])
def update_plan(
    plan_id: str, payload: schemas.PlanUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("account", "account", "edit")),
):
    plan = db.get(Plan, plan_id)
    if plan is None or plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="account", entity="Plan", entity_id=plan.id, action="edit")
    return _plan_out(db, plan)
