import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PortalDashboardOut(BaseModel):
    consumer_name: str
    current_bill_id: Optional[str]
    current_bill_amount: Optional[float]
    current_bill_due_date: Optional[datetime.date]
    total_outstanding: Optional[float]
    plan_name: str
    meter_no: str


class PortalConsumptionPoint(BaseModel):
    period_end: datetime.date
    usage: float


class PortalPaymentOut(BaseModel):
    id: str
    amount: float
    method: str
    paid_at: datetime.datetime
    bill_invoice_no: str


class PortalProfileUpdate(BaseModel):
    contact_no: Optional[str] = None
    billing_address: Optional[str] = Field(None, max_length=250)
