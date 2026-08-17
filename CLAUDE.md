# CLAUDE.md --- UtilityOS End-to-End Multi-Tenant Utility Platform

## 0. Mission

Build a production-style, end-to-end **multi-tenant Utility SaaS
platform** from the uploaded `Utilities(1).xlsx`.

The product must include:

**Super Admin â Utility onboarding â Utility Admin/RBAC â Territory â
Plans/Rates â Consumers â Meters â Meter Reading â VEE â Billing â Bill
Runs â Consumer Portal â Integrations â Audit**

The Excel workbook is the **source of truth for business fields,
terminology, validations, flows, roles and permissions**. Do not invent
conflicting fields or silently remove workbook requirements.

Build a working application with: - Frontend - Backend APIs - PostgreSQL
database - Authentication - RBAC - Tenant isolation - Background
jobs/scheduling - File import/export - PDF bill generation - Seed/demo
data - Tests - API documentation - Docker setup - Production-like error
handling

Do not build a static mockup. Data must persist in the database and all
important UI actions must call real backend APIs.

------------------------------------------------------------------------

# 1. Token/Execution Rules

These rules are mandatory to keep implementation efficient.

1.  **Do not explain the plan repeatedly.**
2.  Work directly from this file and `Utilities(1).xlsx`.
3.  Before coding, inspect the existing repository and reuse working
    code.
4.  Implement in small vertical slices that run end-to-end.
5.  After each phase:
    -   run tests
    -   run build/type checks
    -   fix errors
    -   continue automatically
6.  Do not stop after frontend-only implementation.
7.  Do not create placeholder buttons for core functionality.
8.  Do not ask for confirmation unless a requirement is genuinely
    contradictory.
9.  Prefer simple architecture over unnecessary microservices.
10. Use a **modular monolith** backend.
11. Avoid overengineering.
12. Keep components reusable.
13. Keep API contracts typed.
14. Use migrations, never manually modify production tables.
15. Never expose secrets in frontend code.
16. Never enforce tenant isolation only in the frontend.
17. Add `tenant_id` to every tenant-owned entity and enforce it
    server-side.
18. Use seed data so the entire application can be demonstrated
    immediately.
19. Keep README/docs concise.
20. When a phase is complete, update `IMPLEMENTATION_STATUS.md` with
    only:

-   completed
-   current
-   next

------------------------------------------------------------------------

# 2. Recommended Stack

Use this stack unless the repository already has an equivalent working
stack:

### Frontend

-   Next.js
-   TypeScript
-   Tailwind CSS
-   shadcn/ui
-   React Hook Form
-   Zod
-   TanStack Query
-   Recharts

### Backend

-   FastAPI
-   Python
-   SQLAlchemy
-   Alembic
-   Pydantic

### Database

-   PostgreSQL

### Background jobs

-   Redis
-   Celery or RQ

### Authentication

-   JWT access/refresh tokens
-   bcrypt/argon2 password hashing

### Files

-   Local filesystem in development
-   Storage abstraction so S3-compatible storage can be added later

### Bill generation

-   HTML template â PDF

### Deployment

-   Docker
-   docker-compose

Do not introduce additional infrastructure unless required.

------------------------------------------------------------------------

# 3. Product Architecture

## Platform level

Super Admin manages: - utilities/tenants - platform users - global
roles/permissions - smart meter OEM catalogue - platform configuration -
audit logs - subscription/status

## Tenant level

Each Utility is a tenant.

Utility Admin has full permissions inside its own tenant.

Tenant data must never be visible across tenants.

Hierarchy:

Tenant â Territory â Premise â Consumer â Meter â Meter Reading â Bill

Configuration:

Tenant â Utility Services â Categories/Sub-Categories â Rates â Plans â
Service Charges â Bill Templates â Bill Schedules

------------------------------------------------------------------------

# 4. Roles

Implement configurable RBAC.

Seed these roles from the workbook:

-   SuperAdmin / Admin --- full system access
-   CSR --- full Customer Experience module
-   MX Manager --- full Meter Reading module
-   BX Manager --- full Billing module
-   Validator --- full VEE module
-   Supervisor --- VEE second-level review
-   Meter Reader --- Meter Reading App
-   Consumer --- Consumer Web/Mobile App
-   Property Manager --- assigned consumer data only
-   Field Technician --- Service Order module

Permission model:

`module â resource â action`

Actions: - view - create - edit - delete - approve - execute - export -
download

Do not hard-code permissions into UI components.

------------------------------------------------------------------------

# 5. Authentication & Tenant Security

Implement: - login - logout - refresh token - password hashing -
role-based authorization - tenant context

JWT claims should contain: - user_id - tenant_id - role_ids

Rules: - SuperAdmin may access platform-wide data. - Tenant users may
access only their tenant. - Consumer may access only their own
consumer/account data. - Property Manager may access only assigned
consumers/properties.

Backend must enforce tenant filtering on every tenant-owned query.

------------------------------------------------------------------------

# 6. Super Admin

## Dashboard

Show: - total utilities - active utilities - suspended utilities - total
consumers - total meters - bills generated - failed jobs - integration
status - active users

## Utilities

CRUD: - create utility - edit utility - activate - suspend - view tenant
details

Utility onboarding should create: 1. tenant 2. utility configuration 3.
Utility Admin 4. default roles/permissions 5. default configuration
records

------------------------------------------------------------------------

# 7. Utility Configuration

Use workbook fields.

## Utility

Fields: - Utility Name - Logo - Phone No - Address - Website - Email -
Currency - Time Zone - Date Format - E-Transfer - HST/GST No

Validation from workbook: - Utility Name max 50 - Logo jpg/png/svg, max
2MB - phone E.164 - address max 250 - website http/https - valid email -
currency/timezone/date format required

## Utility Services

Configurable toggle/list: - Water - Sewer - Gas - Electricity

Do not hard-code services in business logic.

------------------------------------------------------------------------

# 8. Territory

Implement cascading hierarchy:

Region â Country â State â City â Zone â Division â Area â Sub-Area â
Premise

Fields/behavior from workbook: - names max 50 where specified - parent
must exist - Sub-Area has Servicable Yes/No - Premise has
Latitude/Longitude - premise selection must drive dependent
auto-population

Create reusable CRUD/list/detail pages for each level.

------------------------------------------------------------------------

# 9. Account Management

## Category

Examples: - Residential - Commercial - Industrial

## Sub-Category

Must depend on Category.

## Rate

Support:

### Fixed

`rate`

### Per Unit Area

`rate`

### Variable

Two bases:

#### Tiered

Example: - 0--15 = 5 - 15--30 = 6.5 - 30+ = 7

#### Time Of Use

Example: - 12 AM--4 PM = 4.5784 - 4 PM--12 AM = 5.67

Build a reusable **rate engine**. Do not hard-code example values.

------------------------------------------------------------------------

# 10. Plans

Fields: - Plan Name - Utility Service(s) - Category - Sub-Category - Tax
% - Billing Frequency - Service/rate components - Rate Type - Rate -
Service Charges

Billing frequency examples: - Monthly - Bi-monthly - Quarterly -
Annually

Tax range: 0--100, max 2 decimals.

Service charges must support: - name - utility service -
fixed/variable - rate

------------------------------------------------------------------------

# 11. Consumer Module

Use workbook fields exactly:

-   Full Name
-   Contact No
-   Email Address
-   SSN
-   ID
-   Premise
-   Service Address
-   Billing Address
-   Plan
-   Activation Date
-   Meter
-   First Meter Reading
-   First Meter Reading Date

Validation: - Full Name required, max 100, alphabets/spaces - Contact
E.164 - Email valid - SSN format XXX-XX-XXXX - ID: pdf/jpg/png, max
5MB - Premise required - Service/Billing address max 250 - Activation
Date cannot be in past - Meter must be assigned/available - initial
reading \>= 0, max 3 decimals - initial reading date \<= today

Consumer creation should support:
`Consumer â Premise â Plan â Meter â Initial Reading`

------------------------------------------------------------------------

# 12. Meter Module

Fields: - Meter No - Device No - Utility Service - Read Type - Premise -
Sub-Area (auto) - Area (auto) - Installation Date - Latitude -
Longitude - Unit - Floor - Meter Dial

Read Types: - Manual - Smart - Photo

Validation: - Meter No max 30; letters/numbers/hyphens - Device No max
30 and unique - installation date \<= today - latitude/longitude valid
numeric values - coordinates up to 7 decimals - unit/floor max 10

Selecting Premise must auto-populate Sub-Area and Area.

------------------------------------------------------------------------

# 13. Routes

Fields: - Route Name - Utility Service(s) - Read Type - Premise -
Sub-Area auto - Area auto - Meter Count auto

Meter Count must come from actual database associations.

------------------------------------------------------------------------

# 14. Read Cycles & Schedules

## Read Cycle

-   Cycle Name
-   Utility Service(s)
-   Read Type
-   Route
-   Meter Count auto

## Schedule

-   Cycle Name
-   Recurring Yes/No
-   Frequency if recurring
-   Start Date
-   Due Days
-   Description

Frequency: - Daily - Weekly - Monthly - Quarterly

Start date cannot be in past.

## Meter Run

No create form.

Schedules generate Meter Runs automatically.

List columns: - Cycle Name - Premise count - Meter count - Utility
Service - readings received - pending

Provide: - template download - meter reading upload

------------------------------------------------------------------------

# 15. Meter Reading

Support: - manual entry - CSV/XLSX upload - reading history - previous
reading/date - current reading/date

Basic validation: - current reading numeric - current reading \>= 0 -
current reading date valid - identify duplicate/invalid readings

Reading upload flow:

Upload â parse â validate â create reading records â VEE â V1/V2 â
Revisit if needed â Completed

Never lose original uploaded data.

------------------------------------------------------------------------

# 16. VEE

## VEE Rules

Fields: - Rule Name - Utility Service - Read Type - Rule - Description

Predefined rule examples from workbook: - No Reading - Threshold Alert

Allow additional rule types through configuration.

## VEE Config

Fields: - Config Name - Utility Service - Read Type - Rule(s)

## VEE Schedule

Fields: - Config - Utility Service auto - Read Type auto - Schedule
Start Date - Repetition Interval - Schedule End Date

Intervals can include: - 15 min - 30 min - 1 hour - other configured
intervals

End date must be after start date.

------------------------------------------------------------------------

# 17. Reading Validation Workflow

Implement statuses:

`Received â V1 â V2 â Revisit â Completed`

Rules: - readings received directly enter V1 - failed V1 enters V2 -
failed V2 can enter Revisit - passed V1 or V2 becomes Completed

Breaks/validation dashboard must show: - Read Cycle - Schedule Start
Date - Schedule End Date - Total Meters - Readings - Pending - V1 - V2 -
Revisit - Completed

Clicking Readings/Completed should show: - Read Cycle - Meter No -
Device No - Previous Reading - Previous Date - Current Reading - Current
Date

------------------------------------------------------------------------

# 18. Billing

## Bill Cycle

Fields: - Cycle Name - Premise - Sub-Area auto - Area auto - Consumer
Count auto

Consumer count must be calculated from consumers associated with
selected premises.

## Bill Template

Support: - Template Name - Template Selection - Field Mapping

Use the workbook's Bill Data Master fields.

## Bill Schedule

Fields: - Bill Cycle - Bill Template - Recurring - Frequency - Bill
Start Date - Bill End Date - Bill Generation Date - Bill Generation
Time - Description

Rules: - recurring frequency required if recurring - start date must be
valid - end date after start - generation date must be future -
generation time valid

------------------------------------------------------------------------

# 19. Bill Run

No create form.

Bill schedules generate Bill Runs.

List: - Cycle Name - Template - Consumer Count - Bill Start Date - Bill
End Date - Status - Action

Action opens Bill Run details.

Details: - Cycle Name - Consumer/Account No - Consumer/Account Name -
Phone - Email - View Bill - Download Bill

------------------------------------------------------------------------

# 20. Billing Engine

Calculation:

`Consumption = Current Reading - Previous Reading`

Then: 1. identify consumer plan 2. identify applicable utility service
3. identify effective rate 4. calculate fixed/per-unit/tiered/TOU charge
5. add service charges 6. calculate tax 7. apply credits/debits 8.
calculate total 9. apply previous outstanding/payment 10. generate bill

Do not calculate billing in frontend.

Billing calculations must be deterministic and unit tested.

------------------------------------------------------------------------

# 21. Bill Data Master

Support these fields where applicable:

-   Account/Consumer No
-   Account/Consumer Name
-   Phone No
-   Email
-   Service Period
-   Invoice Date/Statement Date
-   Invoice No
-   Due Date
-   Service Address
-   Billing Address
-   Utility Website
-   Utility Logo
-   Utility Address
-   Utility Email
-   Utility Phone No
-   GST/HST Registration No
-   E-Transfer Email
-   QR Code
-   Meter Number
-   Utility Service
-   Prev Read Date
-   Prev Reading
-   Current Read Date
-   Current Reading
-   Days(Current-Prev)
-   Usage/Consumption
-   Utility Unit
-   Rate
-   Base Charge
-   Outstanding
-   Total Amount this month excl tax
-   Total Amount this month incl tax
-   Tax amount
-   Payment received since previous bill
-   Late charges
-   Total outstanding amount
-   Extra Charges
-   Credit Note
-   Debit Note
-   Payment History Graph
-   Consumption History Graph
-   Bill Amount History Graph
-   Static Data

------------------------------------------------------------------------

# 22. Bill PDF

Generate real PDFs from stored bill data.

Bill should contain: - utility branding - customer details - invoice
details - meter readings - consumption - rates - charges - taxes -
outstanding - payment information - history charts - static information

Provide: - view - download

------------------------------------------------------------------------

# 23. Consumer Portal

Consumer can: - login - view dashboard - view current bill - view bill
history - download bills - view consumption history - view meter - view
plan - view payment history - update allowed profile fields

Consumer must never access another consumer's data.

------------------------------------------------------------------------

# 24. Smart Meter OEM

Seed the OEM catalogue from workbook:

-   Itron
-   Landis+Gyr
-   Honeywell/Elster
-   ABB Ltd
-   Sensus (Xylem)
-   Badger Meter
-   Kamstrup
-   Aclara (Hubbell)

Store: - OEM - utility services - highlights - integration resources -
links

Do not implement real OEM integrations unless explicitly required.

Instead create an integration abstraction and one **mock smart-meter
provider** that can send readings into the platform.

------------------------------------------------------------------------

# 25. Dashboard

## Utility Admin Dashboard

Show: - active consumers - active meters - meter readings received -
pending readings - V1/V2/revisit counts - completed readings - active
bill cycles - bills generated - billing exceptions - outstanding
amount - collection/payment summary

Charts: - consumption trend - bill amount trend - reading completion -
validation status

Use real DB data.

------------------------------------------------------------------------

# 26. Audit Logs

Record: - user - tenant - timestamp - module - entity - entity ID -
action - old value - new value

Audit: - utility changes - role/permission changes - consumer changes -
meter changes - rate/plan changes - VEE changes - billing configuration
changes - bill generation - user changes

------------------------------------------------------------------------

# 27. Database Core Entities

Create normalized PostgreSQL tables:

Platform: - users - roles - permissions - role_permissions -
user_roles - tenants - audit_logs

Configuration: - utility_services - tenant_services - categories -
sub_categories - rates - rate_tiers - tou_rates - plans -
plan_components - service_charges

Territory: - regions - countries - states - cities - zones - divisions -
areas - sub_areas - premises

Customer: - consumers - consumer_plans - consumer_meters

Metering: - meters - routes - read_cycles - meter_schedules -
meter_runs - meter_readings - vee_rules - vee_configs -
vee_config_rules - vee_schedules - validation_events

Billing: - bill_cycles - bill_templates - bill_template_fields -
bill_schedules - bill_runs - bills - bill_line_items - payments

Integration: - smart_meter_oems - integration_configs -
meter_reading_imports - import_rows

------------------------------------------------------------------------

# 28. API Modules

Create REST endpoints grouped by domain:

`/auth` `/admin` `/tenants` `/users` `/roles` `/permissions` `/services`
`/territory` `/categories` `/rates` `/plans` `/consumers` `/meters`
`/routes` `/read-cycles` `/meter-schedules` `/meter-runs`
`/meter-readings` `/vee` `/bill-cycles` `/bill-templates`
`/bill-schedules` `/bill-runs` `/bills` `/payments` `/reports`
`/integrations` `/audit`

Generate OpenAPI documentation automatically.

------------------------------------------------------------------------

# 29. Frontend Rules

Use: - reusable DataTable - reusable form components - reusable
modal/drawer - reusable confirmation dialog - loading states - empty
states - error states - toast notifications - pagination - search -
filters - sorting

Every CRUD page needs: - list - create - edit - view - delete/deactivate
where applicable

Use React Hook Form + Zod for validation.

Frontend validation should mirror backend validation, but backend
remains authoritative.

------------------------------------------------------------------------

# 30. Background Jobs

Use background workers for: - recurring meter schedules - meter run
generation - VEE schedules - bill schedules - bill run generation - bill
calculation - PDF generation - notification jobs - import processing

Jobs must be idempotent to prevent duplicate runs/bills.

------------------------------------------------------------------------

# 31. File Uploads

Support: - utility logos - consumer ID documents - meter reading
XLSX/CSV - bill template assets

Validate: - extension - MIME type - file size

Never trust client-provided file extension alone.

------------------------------------------------------------------------

# 32. Seed Data

Create demo tenant:

**Demo Water Utility**

Services: - Water - Sewer

Territory: - Region - Country - State - City - Zone - Division - Area -
Sub-Area - multiple Premises

Create: - categories - subcategories - rates - tiered rate - TOU rate -
plans - service charges - consumers - meters - routes - read cycles -
readings - VEE rules/config - bills - payments

Create demo accounts: - superadmin - utilityadmin - csr - mxmanager -
bxmanager - validator - supervisor - meterreader - consumer

Credentials must be documented in development-only seed documentation,
never hard-coded into production.

------------------------------------------------------------------------

# 33. Testing

Minimum tests:

### Unit

-   rate calculations
-   tiered calculations
-   TOU calculations
-   tax
-   consumption
-   billing totals
-   VEE rules
-   permission checks

### API

-   authentication
-   tenant isolation
-   CRUD
-   bill generation
-   file import

### Integration

Test:

`Create Utility â Configure â Consumer â Meter â Reading â VEE â Bill`

### Frontend

Test critical flows: - login - create consumer - create meter - upload
reading - view bill

------------------------------------------------------------------------

# 34. Required Demo Journey

The finished application must support this exact demo without manual DB
edits:

1.  Login as SuperAdmin.
2.  Create a Utility.
3.  Create Utility Admin.
4.  Login as Utility Admin.
5.  Enable Water/Sewer.
6.  Configure territory.
7.  Create category/sub-category.
8.  Create rate.
9.  Create plan.
10. Create service charge.
11. Create premise.
12. Create consumer.
13. Create meter.
14. Create route.
15. Create read cycle.
16. Schedule reading.
17. Generate Meter Run.
18. Upload meter readings.
19. Run VEE.
20. Resolve V1/V2/revisit.
21. Create Bill Cycle.
22. Configure Bill Template.
23. Create Bill Schedule.
24. Generate Bill Run.
25. Calculate bills.
26. View/download generated PDF.
27. Login as Consumer.
28. View the bill and consumption.
29. Verify tenant isolation.
30. Verify audit log.

If this journey works, the core product is complete.

------------------------------------------------------------------------

# 35. UI Quality

Make it look like a modern B2B SaaS product.

Prioritize: - clean sidebar - clear hierarchy - compact tables - strong
filters - professional forms - responsive design - accessible
components - consistent status badges - useful dashboards

Do not spend excessive time on animations.

Functionality \> visual effects.

------------------------------------------------------------------------

# 36. Implementation Order

Implement in these phases, in order:

### Phase 1

Repository + DB + Docker + Auth + RBAC + Tenant isolation

### Phase 2

Super Admin + Utility onboarding + Utility Admin

### Phase 3

Territory + Services + Categories + Rates + Plans

### Phase 4

Consumers + Premises + Meters

### Phase 5

Routes + Read Cycles + Meter Schedules + Meter Runs

### Phase 6

Meter Reading Upload + VEE + V1/V2/Revisit

### Phase 7

Billing Engine + Bill Cycle + Templates + Schedules + Bill Runs

### Phase 8

PDF Bills + Consumer Portal + Payments

### Phase 9

OEM catalogue + Mock Meter API + Audit + Reports

### Phase 10

Tests + Seed data + Docker + API docs + production polish

------------------------------------------------------------------------

# 37. Definition of Done

Do not consider the project complete until:

-   frontend runs
-   backend runs
-   PostgreSQL runs
-   migrations work from clean DB
-   seed data works
-   login works
-   RBAC works
-   tenant isolation is tested
-   all core workbook workflows work
-   forms use workbook fields
-   workbook validations are implemented
-   meter reading upload works
-   VEE workflow works
-   billing calculations are real
-   bill runs work
-   PDF bills work
-   consumer portal works
-   audit logs work
-   API docs work
-   automated tests pass
-   Docker compose starts the entire stack

------------------------------------------------------------------------

# 38. Source-of-Truth Note

`Utilities(1).xlsx` contains: - Index - Onboarding Data - Consumer
Table - Meter Table - Bill Table - Bill Data Master - Flowcharts - Smart
Meter OEM - Roles & Permissions

Use those sheets as the primary product specification.

Where the workbook specifies a field, validation, role, flow, status or
behavior, implement it.

Where the workbook is silent, choose the simplest reasonable
implementation consistent with this architecture.

Do not silently change terminology.

------------------------------------------------------------------------

# 39. Final Instruction to Claude Code

Start by inspecting the repository and the workbook.

Then implement **Phase 1 immediately**.

Do not generate a long explanation before coding.

After each phase, run the relevant tests/build and continue to the next
phase.

The goal is a **fully working end-to-end application**, not a prototype
or frontend mockup.
