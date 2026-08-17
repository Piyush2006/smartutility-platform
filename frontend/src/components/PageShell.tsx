"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { fetchMe, isAuthenticated, logout } from "@/lib/auth";

// tenantOnly items need a tenant_id (SuperAdmin has none -- every one of
// these would 403). superadminOnly items are platform-wide and only make
// sense for SuperAdmin. `module` matches a backend permission module
// (see app/services/rbac_catalog.py) -- items are hidden unless the
// user's roles actually grant that module, straight from /auth/me's
// permission_modules (never hard-coded per-role in the frontend).
const ADMIN_NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/utilities", label: "Utilities", superadminOnly: true },
  { href: "/services", label: "Services", tenantOnly: true, module: "tenant" },
  { href: "/territory", label: "Territory", tenantOnly: true, module: "territory" },
  { href: "/account", label: "Categories & Rates", tenantOnly: true, module: "account" },
  { href: "/plans", label: "Plans", tenantOnly: true, module: "account" },
  { href: "/consumers", label: "Consumers", tenantOnly: true, module: "consumer" },
  { href: "/meters", label: "Meters & Routes", tenantOnly: true, module: "meter" },
  { href: "/readings", label: "Meter Readings", tenantOnly: true, module: "reading" },
  { href: "/vee", label: "VEE", tenantOnly: true, module: "vee" },
  { href: "/billing", label: "Billing", tenantOnly: true, module: "billing" },
  { href: "/users", label: "Users & Roles", tenantOnly: true, module: "users" },
];

const CONSUMER_NAV = [
  { href: "/portal", label: "Dashboard" },
  { href: "/portal/bills", label: "Bills" },
  { href: "/portal/consumption", label: "Consumption" },
  { href: "/portal/profile", label: "Profile" },
];

export function PageShell({ children, title }: { children: React.ReactNode; title: string }) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isAuthenticated()) router.replace("/login");
  }, [router]);

  const meQuery = useQuery({ queryKey: ["me"], queryFn: fetchMe, enabled: isAuthenticated() });
  const me = meQuery.data;
  const isConsumer = me?.roles.some((r) => r.name === "Consumer") && !me?.is_superadmin;
  // While /auth/me is still loading, show nothing rather than guessing --
  // otherwise a SuperAdmin briefly sees (and can click) tenant-only links.
  const nav = !me
    ? []
    : isConsumer
      ? CONSUMER_NAV
      : ADMIN_NAV.filter((item) => {
          if (item.superadminOnly) return !!me.is_superadmin;
          if (item.tenantOnly) {
            if (me.is_superadmin) return false;
            if (!item.module) return true; // Dashboard has no module gate
            return me.permission_modules.includes(item.module);
          }
          return true;
        });

  return (
    <div className="flex min-h-screen flex-1">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white px-3 py-6">
        <div className="px-3 pb-6 text-lg font-semibold text-slate-900">UtilityOS</div>
        <nav className="space-y-0.5">
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded-md px-3 py-2 text-sm font-medium ${
                  active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <h1 className="text-base font-semibold text-slate-900">{title}</h1>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            {me && (
              <span>
                {me.full_name} · {me.roles.map((r) => r.name).join(", ") || (me.is_superadmin ? "SuperAdmin" : "")}
              </span>
            )}
            <button onClick={logout} className="font-medium text-slate-600 hover:text-slate-900">
              Log out
            </button>
          </div>
        </header>
        <main className="flex-1 bg-slate-50 px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
