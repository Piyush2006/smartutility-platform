"""
Consumer Portal (workbook §23). Every route resolves the caller's OWN
Consumer row from the JWT (never from a client-supplied consumer_id) --
"Consumer must never access another consumer's data."
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.account import Plan
from app.models.billing import Bill, Payment
from app.models.consumer import Consumer
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.schemas.billing import BillOut
from app.schemas.consumer import ConsumerOut
from app.schemas.meter import MeterOut
from app.schemas.portal import PortalConsumptionPoint, PortalDashboardOut, PortalPaymentOut, PortalProfileUpdate
from app.services.pdf_generator import generate_bill_pdf

router = APIRouter(prefix="/portal", tags=["portal"])


def _own_consumer(db: Session, current: CurrentUser) -> Consumer:
    consumer = db.execute(select(Consumer).where(Consumer.user_id == current.id)).scalar_one_or_none()
    if consumer is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has no consumer profile.")
    return consumer


@router.get("/dashboard", response_model=PortalDashboardOut)
def dashboard(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    plan = db.get(Plan, consumer.plan_id)
    meter = db.get(Meter, consumer.meter_id)
    latest_bill = db.execute(select(Bill).where(Bill.consumer_id == consumer.id).order_by(Bill.invoice_date.desc(), Bill.created_at.desc())).scalars().first()
    return PortalDashboardOut(
        consumer_name=consumer.full_name,
        current_bill_id=latest_bill.id if latest_bill else None,
        current_bill_amount=float(latest_bill.total_incl_tax) if latest_bill else None,
        current_bill_due_date=latest_bill.due_date if latest_bill else None,
        total_outstanding=latest_bill.remaining_balance if latest_bill else 0.0,
        plan_name=plan.name if plan else "",
        meter_no=meter.meter_no if meter else "",
    )


@router.get("/bills", response_model=list[BillOut])
def bill_history(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    return list(db.execute(select(Bill).where(Bill.consumer_id == consumer.id).order_by(Bill.invoice_date.desc(), Bill.created_at.desc())).scalars())


@router.get("/bills/{bill_id}", response_model=BillOut)
def bill_detail(bill_id: str, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    bill = db.get(Bill, bill_id)
    if bill is None or bill.consumer_id != consumer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


@router.get("/bills/{bill_id}/pdf")
def bill_pdf(bill_id: str, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    bill = db.get(Bill, bill_id)
    if bill is None or bill.consumer_id != consumer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    if not bill.pdf_url:
        bill.pdf_url = generate_bill_pdf(db, bill)
        db.commit()
    file_path = f"{settings.UPLOAD_DIR}/bills/{bill.invoice_no}.pdf"
    return FileResponse(file_path, media_type="application/pdf", filename=f"{bill.invoice_no}.pdf", content_disposition_type="inline")


@router.get("/consumption", response_model=list[PortalConsumptionPoint])
def consumption_history(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    readings = list(
        db.execute(
            select(MeterReading).where(MeterReading.meter_id == consumer.meter_id, MeterReading.status == "Completed").order_by(MeterReading.current_reading_date)
        ).scalars()
    )
    points = []
    for r in readings:
        if r.previous_reading is not None:
            points.append(PortalConsumptionPoint(period_end=r.current_reading_date, usage=float(r.current_reading) - float(r.previous_reading)))
    return points


@router.get("/meter", response_model=MeterOut)
def my_meter(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    meter = db.get(Meter, consumer.meter_id)
    if meter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No meter assigned.")
    return meter


@router.get("/plan")
def my_plan(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    plan = db.get(Plan, consumer.plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan assigned.")
    return {"id": plan.id, "name": plan.name, "billing_frequency": plan.billing_frequency, "tax_percent": plan.tax_percent}


@router.get("/payments", response_model=list[PortalPaymentOut])
def payment_history(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    payments = list(db.execute(select(Payment).where(Payment.consumer_id == consumer.id).order_by(Payment.paid_at.desc())).scalars())
    out = []
    for p in payments:
        bill = db.get(Bill, p.bill_id)
        out.append(PortalPaymentOut(id=p.id, amount=float(p.amount), method=p.method, paid_at=p.paid_at, bill_invoice_no=bill.invoice_no if bill else ""))
    return out


@router.get("/profile", response_model=ConsumerOut)
def my_profile(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return _own_consumer(db, current)


@router.patch("/profile", response_model=ConsumerOut)
def update_my_profile(payload: PortalProfileUpdate, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    consumer = _own_consumer(db, current)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(consumer, key, value)
    db.commit()
    db.refresh(consumer)
    return consumer
