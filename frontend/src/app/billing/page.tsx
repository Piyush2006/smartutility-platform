"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { SimpleCrud } from "@/components/SimpleCrud";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { Modal } from "@/components/Modal";
import { PdfLink } from "@/components/PdfLink";
import { api } from "@/lib/api";
import type { BillDetailOut, BillOut, BillRunDetailRow, BillRunOut, BillScheduleOut } from "@/lib/types";

const TABS = ["Bill Cycles", "Bill Templates", "Bill Schedules", "Bill Runs", "Bills & Payments"] as const;

function BillSchedulesTab() {
  const queryClient = useQueryClient();
  const generateMutation = useMutation({
    mutationFn: async (id: string) => (await api.post(`/bill-schedules/${id}/generate-run`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bill-runs"] }),
  });
  return (
    <div>
      {generateMutation.isError && <div className="mb-4"><ErrorText error={generateMutation.error} /></div>}
    <SimpleCrud<BillScheduleOut>
      resourceKey="bill-schedules" endpoint="/bill-schedules" title="Bill Schedules" canDelete={false}
      fields={[
        { name: "bill_cycle_id", label: "Bill Cycle", type: "select", required: true, optionsEndpoint: "/bill-cycles", readOnlyOnEdit: true },
        { name: "bill_template_id", label: "Bill Template", type: "select", required: true, optionsEndpoint: "/bill-templates", readOnlyOnEdit: true },
        { name: "recurring", label: "Recurring", type: "checkbox", readOnlyOnEdit: true },
        { name: "frequency", label: "Frequency", type: "select", options: ["Monthly", "Bi-monthly", "Quarterly", "Annually"].map((v) => ({ value: v, label: v })), readOnlyOnEdit: true },
        { name: "bill_start_date", label: "Bill Start Date", type: "date", required: true, readOnlyOnEdit: true },
        { name: "bill_end_date", label: "Bill End Date", type: "date", required: true, readOnlyOnEdit: true },
        { name: "bill_generation_date", label: "Bill Generation Date", type: "date", required: true, readOnlyOnEdit: true },
        { name: "bill_generation_time", label: "Bill Generation Time", type: "text", required: true, readOnlyOnEdit: true },
        { name: "is_active", label: "Active", type: "checkbox" },
        { name: "description", label: "Description", type: "text" },
      ]}
      columns={[
        { key: "bill_cycle_id", label: "Bill Cycle" },
        { key: "bill_generation_date", label: "Generation Date" },
        { key: "is_active", label: "Active", render: (s) => <StatusBadge status={s.is_active ? "Active" : "Inactive"} tone={s.is_active ? "green" : "slate"} /> },
        {
          key: "generate", label: "",
          render: (s) => <button onClick={() => generateMutation.mutate(s.id)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">Generate Run</button>,
        },
      ]}
    />
    </div>
  );
}

function BillRunsTab() {
  const [selected, setSelected] = useState<BillRunOut | null>(null);
  const runsQuery = useQuery({ queryKey: ["bill-runs"], queryFn: async () => (await api.get<BillRunOut[]>("/bill-runs")).data });
  const detailQuery = useQuery({
    queryKey: ["bill-run-detail", selected?.id],
    queryFn: async () => (await api.get<BillRunDetailRow[]>(`/bill-runs/${selected!.id}/bills`)).data,
    enabled: !!selected,
  });

  return (
    <div>
      {runsQuery.isError && <div className="mb-4"><ErrorText error={runsQuery.error} /></div>}
      <DataTable<BillRunOut>
        columns={[
          { key: "bill_start_date", label: "Bill Start" },
          { key: "bill_end_date", label: "Bill End" },
          { key: "consumer_count", label: "Consumers" },
          { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} tone={r.status === "completed" ? "green" : r.status === "failed" ? "red" : "amber"} /> },
          { key: "id", label: "Action", render: (r) => <button onClick={() => setSelected(r)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View</button> },
        ]}
        rows={runsQuery.data ?? []}
        emptyLabel="No bill runs yet -- generate one from the Bill Schedules tab."
      />

      {selected && (
        <Modal title="Bill Run Detail" onClose={() => setSelected(null)}>
          <div className="space-y-2">
            {detailQuery.isError && <ErrorText error={detailQuery.error} />}
            {detailQuery.isLoading && <p className="text-sm text-slate-400">Loading…</p>}
            {detailQuery.data?.map((row) => (
              <div key={row.bill_id} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-sm">
                <div>
                  <p className="font-medium text-slate-800">{row.consumer_name}</p>
                  <p className="text-xs text-slate-400">{row.invoice_no} · ${row.total_incl_tax.toFixed(2)}</p>
                </div>
                {row.pdf_url && (
                  <PdfLink url={`/bills/${row.bill_id}/pdf`} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">
                    View PDF
                  </PdfLink>
                )}
              </div>
            ))}
            {detailQuery.data?.length === 0 && <p className="text-sm text-slate-400">No bills in this run.</p>}
          </div>
        </Modal>
      )}
    </div>
  );
}

function BillViewModal({ billId, onClose }: { billId: string; onClose: () => void }) {
  const detailQuery = useQuery({ queryKey: ["bill-detail", billId], queryFn: async () => (await api.get<BillDetailOut>(`/bills/${billId}/detail`)).data });
  const bill = detailQuery.data;

  return (
    <Modal title={bill ? `Invoice ${bill.invoice_no}` : "Invoice"} onClose={onClose}>
      {detailQuery.isLoading && <p className="text-sm text-slate-400">Loading…</p>}
      {detailQuery.isError && <ErrorText error={detailQuery.error} />}
      {bill && (
        <div className="space-y-4 text-sm">
          <div className="grid grid-cols-2 gap-3 rounded-md bg-slate-50 p-3">
            <div><span className="text-slate-400">Consumer:</span> {bill.consumer_name}</div>
            <div><span className="text-slate-400">Status:</span> <StatusBadge status={bill.status} tone={bill.status === "paid" ? "green" : bill.status === "partially_paid" ? "amber" : "slate"} /></div>
            <div><span className="text-slate-400">Email:</span> {bill.consumer_email}</div>
            <div><span className="text-slate-400">Phone:</span> {bill.consumer_phone}</div>
            <div className="col-span-2"><span className="text-slate-400">Service Address:</span> {bill.service_address}</div>
            <div><span className="text-slate-400">Invoice Date:</span> {bill.invoice_date}</div>
            <div><span className="text-slate-400">Due Date:</span> {bill.due_date}</div>
            <div className="col-span-2"><span className="text-slate-400">Service Period:</span> {bill.service_period_start} – {bill.service_period_end}</div>
            <div><span className="text-slate-400">Usage:</span> {bill.usage}</div>
          </div>

          <div>
            <p className="mb-1 font-medium text-slate-700">Charges</p>
            <table className="w-full text-sm">
              <tbody>
                {bill.line_items.map((li) => (
                  <tr key={li.id} className="border-t border-slate-100">
                    <td className="py-1 text-slate-600">{li.label}</td>
                    <td className="py-1 text-right">${li.amount.toFixed(2)}</td>
                  </tr>
                ))}
                <tr className="border-t border-slate-200 font-medium">
                  <td className="py-1">Total (excl. tax)</td>
                  <td className="py-1 text-right">${bill.total_excl_tax.toFixed(2)}</td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-600">Tax</td>
                  <td className="py-1 text-right">${bill.tax_amount.toFixed(2)}</td>
                </tr>
                <tr className="font-medium">
                  <td className="py-1">Total (incl. tax)</td>
                  <td className="py-1 text-right">${bill.total_incl_tax.toFixed(2)}</td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-600">Previous Outstanding</td>
                  <td className="py-1 text-right">${bill.previous_outstanding.toFixed(2)}</td>
                </tr>
                <tr className="border-t border-slate-200 bg-slate-50 font-semibold">
                  <td className="py-1">Total Outstanding (at time of billing)</td>
                  <td className="py-1 text-right">${bill.total_outstanding.toFixed(2)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div>
            <p className="mb-1 font-medium text-slate-700">Payments</p>
            {bill.payments.length === 0 ? (
              <p className="text-xs text-slate-400">No payments recorded against this bill.</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {bill.payments.map((p) => (
                    <tr key={p.id} className="border-t border-slate-100">
                      <td className="py-1 text-slate-600">{new Date(p.paid_at).toLocaleDateString()} · {p.method}</td>
                      <td className="py-1 text-right">${p.amount.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="mt-2 flex justify-between border-t border-slate-200 pt-2 text-sm font-semibold">
              <span>Remaining Balance</span>
              <span>${bill.remaining_balance.toFixed(2)}</span>
            </div>
          </div>

          {bill.pdf_url && (
            <PdfLink url={`/bills/${bill.id}/pdf`} className="inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              Open PDF
            </PdfLink>
          )}
        </div>
      )}
    </Modal>
  );
}

function BillsAndPaymentsTab() {
  const queryClient = useQueryClient();
  const [payingBillId, setPayingBillId] = useState<string | null>(null);
  const [viewingBillId, setViewingBillId] = useState<string | null>(null);
  const billsQuery = useQuery({ queryKey: ["bills"], queryFn: async () => (await api.get<BillOut[]>("/bills")).data });
  const { register, handleSubmit, reset } = useForm<{ amount: number; method: string; reference?: string }>({ defaultValues: { method: "e_transfer" } });

  const payMutation = useMutation({
    mutationFn: async (values: { amount: number; method: string; reference?: string }) =>
      (await api.post("/payments", { ...values, amount: Number(values.amount), bill_id: payingBillId })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      queryClient.invalidateQueries({ queryKey: ["bill-detail"] });
      setPayingBillId(null);
      reset();
    },
  });

  return (
    <div>
      {billsQuery.isError && <div className="mb-4"><ErrorText error={billsQuery.error} /></div>}
      <DataTable<BillOut>
        columns={[
          { key: "invoice_no", label: "Invoice No" },
          { key: "invoice_date", label: "Date" },
          { key: "due_date", label: "Due Date" },
          { key: "usage", label: "Usage" },
          { key: "total_incl_tax", label: "Total", render: (b) => `$${b.total_incl_tax.toFixed(2)}` },
          { key: "remaining_balance", label: "Outstanding", render: (b) => `$${b.remaining_balance.toFixed(2)}` },
          { key: "status", label: "Status", render: (b) => <StatusBadge status={b.status} tone={b.status === "paid" ? "green" : b.status === "partially_paid" ? "amber" : "slate"} /> },
          {
            key: "id", label: "Action",
            render: (b) => (
              <div className="flex gap-3">
                <button onClick={() => setViewingBillId(b.id)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View</button>
                {b.pdf_url && <PdfLink url={`/bills/${b.id}/pdf`} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">PDF</PdfLink>}
                <button onClick={() => setPayingBillId(b.id)} className="text-xs font-medium text-slate-600 underline">Record Payment</button>
              </div>
            ),
          },
        ]}
        rows={billsQuery.data ?? []}
        emptyLabel="No bills yet -- generate a Bill Run from the Bill Schedules tab."
      />

      {viewingBillId && <BillViewModal billId={viewingBillId} onClose={() => setViewingBillId(null)} />}

      {payingBillId && (
        <Modal title="Record Payment" onClose={() => setPayingBillId(null)}>
          <form onSubmit={handleSubmit((v) => payMutation.mutate(v))} className="space-y-3">
            <input type="number" step="any" placeholder="Amount" {...register("amount", { required: true })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            <select {...register("method")} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
              {["e_transfer", "card", "bank_transfer", "cash", "cheque"].map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <input placeholder="Reference (optional)" {...register("reference")} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            <ErrorText error={payMutation.error} />
            <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Record Payment</button>
          </form>
        </Modal>
      )}
    </div>
  );
}

export default function BillingPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Bill Cycles");

  return (
    <PageShell title="Billing">
      <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-t-md px-3 py-2 text-sm font-medium ${tab === t ? "border-b-2 border-slate-900 text-slate-900" : "text-slate-500 hover:text-slate-800"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Bill Cycles" && (
        <SimpleCrud
          resourceKey="bill-cycles" endpoint="/bill-cycles" title="Bill Cycles" canDelete={false}
          fields={[
            { name: "name", label: "Cycle Name", type: "text", required: true },
            { name: "premise_ids", label: "Premise", type: "multiselect", required: true, optionsEndpoint: "/premises", readOnlyOnEdit: true },
          ]}
          columns={[{ key: "name", label: "Name" }, { key: "consumer_count", label: "Consumer Count" }]}
        />
      )}

      {tab === "Bill Templates" && (
        <SimpleCrud
          resourceKey="bill-templates" endpoint="/bill-templates" title="Bill Templates" canDelete={false}
          fields={[{ name: "name", label: "Template Name", type: "text", required: true }]}
          columns={[{ key: "name", label: "Name" }, { key: "template_key", label: "Template" }]}
        />
      )}

      {tab === "Bill Schedules" && <BillSchedulesTab />}
      {tab === "Bill Runs" && <BillRunsTab />}
      {tab === "Bills & Payments" && <BillsAndPaymentsTab />}
    </PageShell>
  );
}
