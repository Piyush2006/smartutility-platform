import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.models.billing import (
    Bill,
    BillCycle,
    BillCyclePremise,
    BillRun,
    BillSchedule,
    BillTemplate,
    BillTemplateField,
    Payment,
)
from app.models.billing import BillLineItem
from app.models.consumer import Consumer
from app.schemas import billing as schemas
from app.services.audit import record_audit
from app.services.bill_run_engine import generate_bill_run
from app.services.pdf_generator import generate_bill_pdf

router = APIRouter(tags=["billing"])


# ---- Bill Cycle -------------------------------------------------------

def _cycle_out(db: Session, cycle: BillCycle) -> schemas.BillCycleOut:
    premise_ids = [r[0] for r in db.execute(select(BillCyclePremise.premise_id).where(BillCyclePremise.bill_cycle_id == cycle.id)).all()]
    consumer_count = db.execute(select(func.count()).select_from(Consumer).where(Consumer.premise_id.in_(premise_ids))).scalar_one() if premise_ids else 0
    return schemas.BillCycleOut(id=cycle.id, tenant_id=cycle.tenant_id, name=cycle.name, premise_ids=premise_ids, consumer_count=consumer_count)


@router.get("/bill-cycles", response_model=list[schemas.BillCycleOut])
def list_bill_cycles(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    cycles = list(db.execute(select(BillCycle).where(BillCycle.tenant_id == tenant_id)).scalars())
    return [_cycle_out(db, c) for c in cycles]


@router.post("/bill-cycles", response_model=schemas.BillCycleOut, status_code=status.HTTP_201_CREATED)
def create_bill_cycle(
    payload: schemas.BillCycleCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "create")),
):
    cycle = BillCycle(tenant_id=tenant_id, name=payload.name)
    db.add(cycle)
    db.flush()
    for premise_id in payload.premise_ids:
        db.add(BillCyclePremise(bill_cycle_id=cycle.id, premise_id=premise_id))
    db.commit()
    db.refresh(cycle)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="BillCycle", entity_id=cycle.id, action="create", new_value=payload.model_dump(mode="json"))
    return _cycle_out(db, cycle)


@router.get("/bill-cycles/{cycle_id}", response_model=schemas.BillCycleOut, tags=["billing"])
def get_bill_cycle(cycle_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    cycle = db.get(BillCycle, cycle_id)
    if cycle is None or cycle.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill cycle not found")
    return _cycle_out(db, cycle)


@router.patch("/bill-cycles/{cycle_id}", response_model=schemas.BillCycleOut, tags=["billing"])
def update_bill_cycle(
    cycle_id: str, payload: schemas.BillCycleUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "edit")),
):
    cycle = db.get(BillCycle, cycle_id)
    if cycle is None or cycle.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill cycle not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cycle, key, value)
    db.commit()
    db.refresh(cycle)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="BillCycle", entity_id=cycle.id, action="edit")
    return _cycle_out(db, cycle)


# ---- Bill Template ----------------------------------------------------

def _template_out(db: Session, tmpl: BillTemplate) -> schemas.BillTemplateOut:
    fields = list(db.execute(select(BillTemplateField).where(BillTemplateField.bill_template_id == tmpl.id).order_by(BillTemplateField.sort_order)).scalars())
    return schemas.BillTemplateOut(id=tmpl.id, tenant_id=tmpl.tenant_id, name=tmpl.name, template_key=tmpl.template_key, fields=[schemas.BillTemplateFieldOut.model_validate(f) for f in fields])


@router.get("/bill-templates", response_model=list[schemas.BillTemplateOut])
def list_bill_templates(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    templates = list(db.execute(select(BillTemplate).where(BillTemplate.tenant_id == tenant_id)).scalars())
    return [_template_out(db, t) for t in templates]


@router.post("/bill-templates", response_model=schemas.BillTemplateOut, status_code=status.HTTP_201_CREATED)
def create_bill_template(
    payload: schemas.BillTemplateCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "create")),
):
    tmpl = BillTemplate(tenant_id=tenant_id, name=payload.name, template_key=payload.template_key)
    db.add(tmpl)
    db.flush()
    for f in payload.fields:
        db.add(BillTemplateField(tenant_id=tenant_id, bill_template_id=tmpl.id, field_key=f.field_key, is_enabled=f.is_enabled, sort_order=f.sort_order))
    db.commit()
    db.refresh(tmpl)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="BillTemplate", entity_id=tmpl.id, action="create")
    return _template_out(db, tmpl)


@router.get("/bill-templates/{template_id}", response_model=schemas.BillTemplateOut, tags=["billing"])
def get_bill_template(template_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    tmpl = db.get(BillTemplate, template_id)
    if tmpl is None or tmpl.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill template not found")
    return _template_out(db, tmpl)


@router.patch("/bill-templates/{template_id}", response_model=schemas.BillTemplateOut, tags=["billing"])
def update_bill_template(
    template_id: str, payload: schemas.BillTemplateUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "edit")),
):
    tmpl = db.get(BillTemplate, template_id)
    if tmpl is None or tmpl.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill template not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tmpl, key, value)
    db.commit()
    db.refresh(tmpl)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="BillTemplate", entity_id=tmpl.id, action="edit")
    return _template_out(db, tmpl)


# ---- Bill Schedule + Run ------------------------------------------------

@router.get("/bill-schedules", response_model=list[schemas.BillScheduleOut])
def list_bill_schedules(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    return list(db.execute(select(BillSchedule).where(BillSchedule.tenant_id == tenant_id)).scalars())


@router.post("/bill-schedules", response_model=schemas.BillScheduleOut, status_code=status.HTTP_201_CREATED)
def create_bill_schedule(
    payload: schemas.BillScheduleCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "create")),
):
    schedule = BillSchedule(tenant_id=tenant_id, **payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="BillSchedule", entity_id=schedule.id, action="create", new_value=payload.model_dump(mode="json"))
    return schedule


@router.get("/bill-schedules/{schedule_id}", response_model=schemas.BillScheduleOut, tags=["billing"])
def get_bill_schedule(schedule_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    schedule = db.get(BillSchedule, schedule_id)
    if schedule is None or schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill schedule not found")
    return schedule


@router.patch("/bill-schedules/{schedule_id}", response_model=schemas.BillScheduleOut, tags=["billing"])
def update_bill_schedule(
    schedule_id: str, payload: schemas.BillScheduleUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "edit")),
):
    schedule = db.get(BillSchedule, schedule_id)
    if schedule is None or schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill schedule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, key, value)
    db.commit()
    db.refresh(schedule)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="BillSchedule", entity_id=schedule.id, action="edit")
    return schedule


@router.get("/bill-runs", response_model=list[schemas.BillRunOut])
def list_bill_runs(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    return list(db.execute(select(BillRun).where(BillRun.tenant_id == tenant_id)).scalars())


@router.post("/bill-schedules/{schedule_id}/generate-run", response_model=schemas.BillRunOut, status_code=status.HTTP_201_CREATED)
def trigger_bill_run(
    schedule_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "execute")),
):
    """Manual 'Generate Now' -- mirrors the Celery Beat task for due
    recurring schedules in production (app/tasks/billing_tasks.py). Also
    renders + attaches a PDF for every bill produced (workbook §22)."""
    schedule = db.get(BillSchedule, schedule_id)
    if schedule is None or schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    run = generate_bill_run(db, schedule)

    for bill in db.execute(select(Bill).where(Bill.bill_run_id == run.id)).scalars():
        bill.pdf_url = generate_bill_pdf(db, bill)
    db.commit()

    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="BillRun", entity_id=run.id, action="execute", new_value={"status": run.status, "consumer_count": run.consumer_count})
    return run


@router.get("/bill-runs/{run_id}/bills", response_model=list[schemas.BillRunDetailRow])
def bill_run_detail(run_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    run = db.get(BillRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill run not found")
    bills = list(db.execute(select(Bill).where(Bill.bill_run_id == run_id)).scalars())
    rows = []
    for bill in bills:
        consumer = db.get(Consumer, bill.consumer_id)
        rows.append(
            schemas.BillRunDetailRow(
                consumer_id=bill.consumer_id, consumer_name=consumer.full_name if consumer else "", phone_no=consumer.contact_no if consumer else "",
                email=consumer.email_address if consumer else "", bill_id=bill.id, invoice_no=bill.invoice_no,
                total_incl_tax=float(bill.total_incl_tax), pdf_url=bill.pdf_url,
            )
        )
    return rows


# ---- Bills + PDF --------------------------------------------------------

@router.get("/bills", response_model=list[schemas.BillOut])
def list_bills(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    return list(db.execute(select(Bill).where(Bill.tenant_id == tenant_id)).scalars())


@router.get("/bills/{bill_id}", response_model=schemas.BillOut)
def get_bill(bill_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    bill = db.get(Bill, bill_id)
    if bill is None or bill.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


@router.get("/bills/{bill_id}/detail", response_model=schemas.BillDetailOut)
def get_bill_detail(bill_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    """Full on-screen invoice view: bill + consumer info + line items +
    payments applied -- what the Billing screen's 'View' action opens,
    as an alternative to downloading the PDF."""
    bill = db.get(Bill, bill_id)
    if bill is None or bill.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    consumer = db.get(Consumer, bill.consumer_id)
    line_items = list(db.execute(select(BillLineItem).where(BillLineItem.bill_id == bill.id)).scalars())
    payments = list(db.execute(select(Payment).where(Payment.bill_id == bill.id).order_by(Payment.paid_at.desc())).scalars())
    return schemas.BillDetailOut(
        **schemas.BillOut.model_validate(bill).model_dump(),
        consumer_name=consumer.full_name if consumer else "",
        consumer_email=consumer.email_address if consumer else "",
        consumer_phone=consumer.contact_no if consumer else "",
        service_address=consumer.service_address if consumer else "",
        line_items=[schemas.BillLineItemOut.model_validate(li) for li in line_items],
        payments=[schemas.BillDetailPaymentOut.model_validate(p) for p in payments],
    )


@router.get("/bills/{bill_id}/pdf")
def download_bill_pdf(bill_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "download"))):
    bill = db.get(Bill, bill_id)
    if bill is None or bill.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    if not bill.pdf_url:
        bill.pdf_url = generate_bill_pdf(db, bill)
        db.commit()
    file_path = f"{settings.UPLOAD_DIR}/bills/{bill.invoice_no}.pdf"
    return FileResponse(file_path, media_type="application/pdf", filename=f"{bill.invoice_no}.pdf", content_disposition_type="inline")


# ---- Payments -------------------------------------------------------------

@router.get("/payments", response_model=list[schemas.PaymentOut])
def list_payments(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("billing", "billing", "view"))):
    return list(db.execute(select(Payment).where(Payment.tenant_id == tenant_id)).scalars())


@router.post("/payments", response_model=schemas.PaymentOut, status_code=status.HTTP_201_CREATED)
def record_payment(
    payload: schemas.PaymentCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("billing", "billing", "create")),
):
    bill = db.get(Bill, payload.bill_id)
    if bill is None or bill.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a valid bill.")
    payment = Payment(
        tenant_id=tenant_id, bill_id=bill.id, consumer_id=bill.consumer_id, amount=payload.amount,
        method=payload.method, paid_at=datetime.datetime.now(datetime.timezone.utc), reference=payload.reference,
    )
    db.add(payment)

    paid_total = db.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.bill_id == bill.id)).scalar_one()
    paid_total = float(paid_total) + payload.amount
    if paid_total >= float(bill.total_outstanding):
        bill.status = "paid"
    elif paid_total > 0:
        bill.status = "partially_paid"
    db.commit()
    db.refresh(payment)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="billing", entity="Payment", entity_id=payment.id, action="create", new_value=payload.model_dump(mode="json"))
    return payment
