export interface UtilityServiceOut {
  id: string;
  name: string;
}

export interface RoleSummaryOut {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
}

export interface PermissionSummaryOut {
  id: string;
  module: string;
  resource: string;
  action: string;
  description: string | null;
}

export interface RoleDetailOut extends RoleSummaryOut {
  permissions: PermissionSummaryOut[];
}

export interface UserInviteOut {
  user: TenantUserOut;
  email_sent: boolean;
  invite_link: string;
}

export interface TenantUserOut {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  roles: RoleSummaryOut[];
}

export interface TenantServiceOut {
  utility_service_id: string;
  name: string;
  is_enabled: boolean;
}

export interface CategoryOut {
  id: string;
  name: string;
}

export interface SubCategoryOut {
  id: string;
  category_id: string;
  name: string;
}

export interface RateOut {
  id: string;
  name: string;
  rate_type: "fixed" | "per_unit_area" | "variable";
  rate: number | null;
  basis: "tiered" | "time_of_use" | null;
  tiers: { id: string; tier_from: number; tier_to: number | null; price: number }[];
  tou_rates: { id: string; start_time: string; end_time: string; price: number }[];
}

export interface PlanOut {
  id: string;
  name: string;
  category_id: string;
  sub_category_id: string;
  tax_percent: number | null;
  billing_frequency: string | null;
  is_active: boolean;
  components: { id: string; utility_service_id: string; rate_id: string }[];
}

export interface ServiceChargeOut {
  id: string;
  name: string;
  utility_service_id: string | null;
  charge_type: "fixed" | "variable";
  rate: number;
  plan_id: string | null;
}

export interface PremiseOut {
  id: string;
  sub_area_id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
}

export interface MeterOut {
  id: string;
  meter_no: string;
  device_no: string;
  utility_service_id: string;
  read_type: string;
  premise_id: string;
  is_assigned: boolean;
}

export interface RouteOut {
  id: string;
  name: string;
  read_type: string;
  premise_id: string;
  utility_service_ids: string[];
  meter_count: number;
}

export interface ReadCycleOut {
  id: string;
  name: string;
  read_type: string;
  route_id: string;
  utility_service_ids: string[];
  meter_count: number;
}

export interface MeterScheduleOut {
  id: string;
  read_cycle_id: string;
  recurring: boolean;
  frequency: string | null;
  start_date: string;
  due_days: number | null;
  is_active: boolean;
}

export interface MeterRunOut {
  id: string;
  meter_schedule_id: string;
  run_date: string;
  premise_count: number;
  meter_count: number;
  readings_received: number;
  status: string;
}

export interface ConsumerOut {
  id: string;
  full_name: string;
  contact_no: string;
  email_address: string;
  premise_id: string;
  service_address: string;
  billing_address: string;
  plan_id: string;
  meter_id: string;
  activation_date: string;
  first_meter_reading: number;
  first_meter_reading_date: string;
  status: string;
}

export interface VeeScheduleOut {
  id: string;
  vee_config_id: string;
  start_date: string;
  repetition_interval: string;
  end_date: string;
  is_active: boolean;
}

export interface MeterReadingOut {
  id: string;
  meter_id: string;
  meter_run_id: string | null;
  previous_reading: number | null;
  previous_reading_date: string | null;
  current_reading: number;
  current_reading_date: string;
  status: "Received" | "V1" | "V2" | "Revisit" | "Completed";
  source: string;
}

export interface ValidationBreakdownOut {
  read_cycle_id: string;
  read_cycle_name: string;
  total_meters: number;
  readings: number;
  pending: number;
  v1: number;
  v2: number;
  revisit: number;
  completed: number;
}

export interface VeeRuleOut {
  id: string;
  name: string;
  utility_service_id: string;
  read_type: string;
  rule_type: string;
  parameters: Record<string, unknown> | null;
}

export interface VeeConfigOut {
  id: string;
  name: string;
  utility_service_id: string;
  read_type: string;
  rule_ids: string[];
}

export interface BillCycleOut {
  id: string;
  name: string;
  premise_ids: string[];
  consumer_count: number;
}

export interface BillTemplateOut {
  id: string;
  name: string;
  template_key: string;
}

export interface BillScheduleOut {
  id: string;
  bill_cycle_id: string;
  bill_template_id: string;
  recurring: boolean;
  bill_start_date: string;
  bill_end_date: string;
  bill_generation_date: string;
  bill_generation_time: string;
  is_active: boolean;
}

export interface BillRunOut {
  id: string;
  bill_schedule_id: string;
  bill_cycle_id: string;
  bill_template_id: string;
  consumer_count: number;
  bill_start_date: string;
  bill_end_date: string;
  status: string;
}

export interface BillRunDetailRow {
  consumer_id: string;
  consumer_name: string;
  phone_no: string;
  email: string;
  bill_id: string;
  invoice_no: string;
  total_incl_tax: number;
  pdf_url: string | null;
}

export interface BillOut {
  id: string;
  invoice_no: string;
  invoice_date: string;
  due_date: string;
  service_period_start: string;
  service_period_end: string;
  usage: number;
  base_charge: number;
  service_charges_total: number;
  tax_amount: number;
  total_excl_tax: number;
  total_incl_tax: number;
  previous_outstanding: number;
  late_charges: number;
  credit_note: number;
  debit_note: number;
  total_outstanding: number;
  remaining_balance: number;
  status: string;
  pdf_url: string | null;
}

export interface BillLineItemOut {
  id: string;
  label: string;
  kind: string;
  amount: number;
}

export interface BillDetailPaymentOut {
  id: string;
  amount: number;
  method: string;
  paid_at: string;
  reference: string | null;
}

export interface BillDetailOut extends BillOut {
  consumer_name: string;
  consumer_email: string;
  consumer_phone: string;
  service_address: string;
  line_items: BillLineItemOut[];
  payments: BillDetailPaymentOut[];
}

export interface RegionLevelOut {
  id: string;
  name: string;
  [parentKey: string]: unknown;
}
