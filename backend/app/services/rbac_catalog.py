"""
Source-of-truth catalogue for seeded roles & permissions (workbook
'Roles & Permissions' sheet). Reused by:
  - app/services/seed.py (demo tenant)
  - the utility-onboarding flow (clones these roles into every new tenant)

Permission resources are deliberately coarse (one resource per module,
e.g. module="meter", resource="meter") rather than one per table -- the
workbook only ever specifies "full access to the X module", so a finer
grain would add rows without adding real access control.
"""

SYSTEM_ROLES: list[dict] = [
    {"name": "Utility Admin", "description": "Full permissions inside its own tenant"},
    {"name": "CSR", "description": "Full access to the Customer Experience (CX) module"},
    {"name": "MX Manager", "description": "Full access to the Meter Reading (MX) module"},
    {"name": "BX Manager", "description": "Full access to the Billing (BX) module"},
    {"name": "Validator", "description": "Full access to the Validation, Estimation & Editing (VEE) module"},
    {"name": "Supervisor", "description": "Full access to the VEE module (second-level review)"},
    {"name": "Meter Reader", "description": "Access to the Meter Reading App"},
    {"name": "Consumer", "description": "Full access to the Consumer Web & Mobile App"},
    {"name": "Property Manager", "description": "Access only to assigned consumer data"},
    {"name": "Field Technician", "description": "Full access to the Service Order module"},
]

# module -> (resource, [actions], description)
MODULE_ACTIONS: dict[str, list[str]] = {
    "tenant": ["view", "edit"],
    "territory": ["view", "create", "edit", "delete"],
    "account": ["view", "create", "edit", "delete"],
    "consumer": ["view", "create", "edit", "delete", "export", "download"],
    "meter": ["view", "create", "edit", "delete", "execute", "export", "download"],
    "reading": ["view", "create", "edit", "delete", "execute", "export", "download"],
    "vee": ["view", "create", "edit", "delete", "approve", "execute"],
    "billing": ["view", "create", "edit", "delete", "execute", "export", "download"],
    "reports": ["view", "export"],
    "integration": ["view", "create", "edit"],
    "audit": ["view"],
    "portal": ["view", "edit", "download"],
    "users": ["view", "create", "edit", "delete"],
}

MODULE_DESCRIPTIONS: dict[str, str] = {
    "tenant": "View own utility configuration",
    "territory": "Territory hierarchy (Region..Premise)",
    "account": "Categories, Rates, Plans, Service Charges",
    "consumer": "Consumer records",
    "meter": "Meters, Routes, Read Cycles, Schedules, Runs",
    "reading": "Meter readings and uploads",
    "vee": "Validation, Estimation & Editing",
    "billing": "Bill Cycles, Templates, Schedules, Runs, Bills, Payments",
    "reports": "Reporting",
    "integration": "Smart meter OEM integrations",
    "audit": "Audit log",
    "portal": "Consumer's own account (Consumer Portal)",
    "users": "Tenant staff users & role assignment",
}

PERMISSIONS: list[dict] = [
    {"module": "platform", "resource": "tenants", "action": "view", "description": "View all utilities/tenants"},
    {"module": "platform", "resource": "tenants", "action": "create", "description": "Create a utility/tenant"},
    {"module": "platform", "resource": "tenants", "action": "edit", "description": "Edit/activate/suspend a utility/tenant"},
] + [
    {"module": module, "resource": module, "action": action, "description": f"{MODULE_DESCRIPTIONS[module]} -- {action}"}
    for module, actions in MODULE_ACTIONS.items()
    for action in actions
]

# Role name -> list of full-access modules ("full access to the X module").
ROLE_MODULE_ACCESS: dict[str, list[str]] = {
    "Utility Admin": ["tenant", "territory", "account", "consumer", "meter", "reading", "vee", "billing", "reports", "integration", "audit", "users"],
    "CSR": ["consumer", "reports"],
    "MX Manager": ["meter", "reading", "reports"],
    "BX Manager": ["billing", "reports"],
    "Validator": ["vee"],
    "Supervisor": ["vee"],
}

# Roles with hand-picked (not "full module") action sets.
ROLE_EXTRA_PERMISSIONS: dict[str, list[tuple[str, str, str]]] = {
    "Meter Reader": [("meter", "meter", "view"), ("reading", "reading", "view"), ("reading", "reading", "create")],
    "Consumer": [("portal", "portal", "view"), ("portal", "portal", "edit"), ("portal", "portal", "download")],
    "Property Manager": [("consumer", "consumer", "view")],
    "Field Technician": [],  # Service Order module not yet implemented
}


def build_role_permission_defaults() -> dict[str, list[tuple[str, str, str]]]:
    defaults: dict[str, list[tuple[str, str, str]]] = {}
    for role_name, modules in ROLE_MODULE_ACCESS.items():
        defaults[role_name] = [(p["module"], p["resource"], p["action"]) for p in PERMISSIONS if p["module"] in modules]
    for role_name, extra in ROLE_EXTRA_PERMISSIONS.items():
        defaults.setdefault(role_name, [])
        defaults[role_name].extend(extra)
    return defaults


ROLE_PERMISSION_DEFAULTS: dict[str, list[tuple[str, str, str]]] = build_role_permission_defaults()
