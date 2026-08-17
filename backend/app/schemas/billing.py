import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class BillCycleCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    premise_ids: list[str] = Field(..., min_length=1)


class BillCycleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)


class BillCycleOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    premise_ids: list[str] = []
    consumer_count: int = 0
    model_config = {"from_attributes": True}


class BillTemplateFieldIn(BaseModel):
    field_key: str
    is_enabled: bool = True
    sort_order: int = 0


class BillTemplateCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    template_key: str = "standard"
    fields: list[BillTemplateFieldIn] = Field(default_factory=list)


class BillTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)


class BillTemplateFieldOut(BaseModel):
    field_key: str
    is_enabled: bool
    sort_order: int
    model_config = {"from_attributes": True}


class BillTemplateOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    template_key: str
    fields: list[BillTemplateFieldOut] = []
    model_config = {"from_attributes": True}


class BillScheduleCreate(BaseModel):
    bill_cycle_id: str
    bill_template_id: str
    recurring: bool = False
    frequency: Optional[str] = None
    bill_start_date: datetime.date
    bill_end_date: datetime.date
    bill_generation_date: datetime.date
    bill_generation_time: datetime.time
    description: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def _validate(self):
        if self.recurring and not self.frequency:
            raise ValueError("Select a billing frequency for recurring schedules.")
        if self.bill_end_date <= self.bill_start_date:
            raise ValueError("End date must be after the start date.")
        if self.bill_generation_date <= datetime.date.today():
            raise ValueError("Bill generation date must be in the future.")
        return self


class BillScheduleUpdate(BaseModel):
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)


class BillScheduleOut(BaseModel):
    id: str
    tenant_id: str
    bill_cycle_id: str
    bill_template_id: str
    recurring: bool
    frequency: Optional[str]
    bill_start_date: datetime.date
    bill_end_date: datetime.date
    bill_generation_date: datetime.date
    bill_generation_time: datetime.time
    description: Optional[str]
    is_active: bool
    model_config = {"from_attributes": True}


class BillRunOut(BaseModel):
    id: str
    tenant_id: str
    bill_schedule_id: str
    bill_cycle_id: str
    bill_template_id: str
    consumer_count: int
    bill_start_date: datetime.date
    bill_end_date: datetime.date
    status: str
    error_message: Optional[str]
    model_config = {"from_attributes": True}


class BillOut(BaseModel):
    id: str
    tenant_id: str
    bill_run_id: str
    consumer_id: str
    invoice_no: str
    invoice_date: datetime.date
    due_date: datetime.date
    service_period_start: datetime.date
    service_period_end: datetime.date
    usage: float
    base_charge: float
    service_charges_total: float
    tax_amount: float
    total_excl_tax: float
    total_incl_tax: float
    previous_outstanding: float
    late_charges: float
    credit_note: float
    debit_note: float
    total_outstanding: float
    remaining_balance: float  # total_outstanding minus payments applied to this specific bill (never negative)
    status: str
    pdf_url: Optional[str]
    model_config = {"from_attributes": True}


class BillLineItemOut(BaseModel):
    id: str
    label: str
    kind: str
    amount: float
    model_config = {"from_attributes": True}


class BillDetailPaymentOut(BaseModel):
    id: str
    amount: float
    method: str
    paid_at: datetime.datetime
    reference: Optional[str]
    model_config = {"from_attributes": True}


class BillDetailOut(BillOut):
    consumer_name: str
    consumer_email: str
    consumer_phone: str
    service_address: str
    line_items: list[BillLineItemOut] = []
    payments: list[BillDetailPaymentOut] = []


class BillRunDetailRow(BaseModel):
    consumer_id: str
    consumer_name: str
    phone_no: str
    email: str
    bill_id: str
    invoice_no: str
    total_incl_tax: float
    pdf_url: Optional[str]


class PaymentCreate(BaseModel):
    bill_id: str
    amount: float = Field(..., gt=0)
    method: str
    reference: Optional[str] = Field(None, max_length=100)


class PaymentOut(BaseModel):
    id: str
    tenant_id: str
    bill_id: str
    consumer_id: str
    amount: float
    method: str
    paid_at: datetime.datetime
    reference: Optional[str]
    model_config = {"from_attributes": True}
