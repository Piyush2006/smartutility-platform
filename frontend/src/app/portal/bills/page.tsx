"use client";

import { useQuery } from "@tanstack/react-query";
import { PageShell } from "@/components/PageShell";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { PdfLink } from "@/components/PdfLink";
import { api } from "@/lib/api";
import type { BillOut } from "@/lib/types";

export default function PortalBillsPage() {
  const billsQuery = useQuery({ queryKey: ["portal-bills"], queryFn: async () => (await api.get<BillOut[]>("/portal/bills")).data });
  const bills = billsQuery.data ?? [];

  const totalBilled = bills.reduce((sum, b) => sum + b.total_incl_tax, 0);
  // Most-recent bill's remaining_balance already reflects the running
  // outstanding-carry-forward across the whole history (see
  // billing_engine.compute_outstanding), so "paid to date" is simply what
  // was ever billed minus what's still owed right now.
  const outstanding = bills.length ? bills[0].remaining_balance : 0; // most-recent-first from the API
  const totalPaid = Math.max(totalBilled - outstanding, 0);

  return (
    <PageShell title="My Bills">
      {billsQuery.isError ? (
        <ErrorText error={billsQuery.error} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Bills Issued</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{bills.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Total Paid to Date</p>
              <p className="mt-1 text-2xl font-semibold text-emerald-600">${totalPaid.toFixed(2)}</p>
              <p className="mt-1 text-xs text-slate-400">of ${totalBilled.toFixed(2)} billed</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Current Outstanding</p>
              <p className={`mt-1 text-2xl font-semibold ${outstanding > 0 ? "text-amber-600" : "text-slate-900"}`}>${outstanding.toFixed(2)}</p>
            </div>
          </div>

          <DataTable<BillOut>
            columns={[
              { key: "invoice_no", label: "Invoice No" },
              { key: "invoice_date", label: "Date" },
              { key: "due_date", label: "Due Date" },
              { key: "usage", label: "Usage" },
              { key: "total_incl_tax", label: "Amount", render: (b) => `$${b.total_incl_tax.toFixed(2)}` },
              { key: "remaining_balance", label: "Outstanding", render: (b) => `$${b.remaining_balance.toFixed(2)}` },
              { key: "status", label: "Status", render: (b) => <StatusBadge status={b.status} tone={b.status === "paid" ? "green" : b.status === "partially_paid" ? "amber" : "red"} /> },
              {
                key: "id", label: "Action",
                render: (b) => (
                  <PdfLink url={`/portal/bills/${b.id}/pdf`} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">
                    View / Download
                  </PdfLink>
                ),
              },
            ]}
            rows={bills}
            emptyLabel="No bills yet."
          />
        </div>
      )}
    </PageShell>
  );
}
