"use client";

import { useQuery } from "@tanstack/react-query";
import { PageShell } from "@/components/PageShell";
import { ErrorText } from "@/components/ErrorText";
import { PdfLink } from "@/components/PdfLink";
import { api } from "@/lib/api";

interface PortalDashboard {
  consumer_name: string;
  current_bill_id: string | null;
  current_bill_amount: number | null;
  current_bill_due_date: string | null;
  total_outstanding: number | null;
  plan_name: string;
  meter_no: string;
}

export default function PortalDashboardPage() {
  const dashboardQuery = useQuery({ queryKey: ["portal-dashboard"], queryFn: async () => (await api.get<PortalDashboard>("/portal/dashboard")).data });
  const d = dashboardQuery.data;

  return (
    <PageShell title="My Dashboard">
      {dashboardQuery.isError && <ErrorText error={dashboardQuery.error} />}
      {d && (
        <div className="space-y-6">
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <p className="text-sm text-slate-500">Welcome back,</p>
            <p className="text-xl font-semibold text-slate-900">{d.consumer_name}</p>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Current Bill</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{d.current_bill_amount != null ? `$${d.current_bill_amount.toFixed(2)}` : "—"}</p>
              {d.current_bill_due_date && <p className="mt-1 text-xs text-slate-400">Due {d.current_bill_due_date}</p>}
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Total Outstanding</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{d.total_outstanding != null ? `$${d.total_outstanding.toFixed(2)}` : "$0.00"}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Plan / Meter</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{d.plan_name}</p>
              <p className="text-xs text-slate-400">{d.meter_no}</p>
            </div>
          </div>

          {d.current_bill_id && (
            <PdfLink url={`/portal/bills/${d.current_bill_id}/pdf`} className="inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              View / Download Current Bill
            </PdfLink>
          )}
        </div>
      )}
    </PageShell>
  );
}
