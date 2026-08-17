"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { SimpleCrud } from "@/components/SimpleCrud";
import { DataTable } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { Modal } from "@/components/Modal";
import { api } from "@/lib/api";
import type { RateOut } from "@/lib/types";

interface RateForm {
  name: string;
  rate_type: "fixed" | "per_unit_area" | "variable";
  rate?: number;
  basis?: "tiered" | "time_of_use";
  tiers: { tier_from: number; tier_to: number | null; price: number }[];
  tou_rates: { start_time: string; end_time: string; price: number }[];
}

function RateDetailModal({ rate, onClose, onDeleted }: { rate: RateOut; onClose: () => void; onDeleted: () => void }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const { register, handleSubmit, reset } = useForm<{ name: string; rate?: number }>();

  useEffect(() => {
    reset({ name: rate.name, rate: rate.rate ?? undefined });
  }, [rate, reset]);

  const updateMutation = useMutation({
    mutationFn: async (values: { name: string; rate?: number }) => {
      const payload: Record<string, unknown> = { name: values.name };
      if (rate.rate_type !== "variable") payload.rate = Number(values.rate);
      return (await api.patch(`/rates/${rate.id}`, payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rates"] });
      onClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => api.delete(`/rates/${rate.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rates"] });
      onDeleted();
    },
  });

  return (
    <Modal title={editing ? `Edit ${rate.name}` : rate.name} onClose={onClose}>
      {editing ? (
        <form onSubmit={handleSubmit((v) => updateMutation.mutate(v))} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Rate Name</label>
            <input {...register("name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
          </div>
          {rate.rate_type !== "variable" && (
            <div>
              <label className="block text-sm font-medium text-slate-700">Rate ($)</label>
              <input type="number" step="any" {...register("rate", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
          )}
          <p className="text-xs text-slate-400">Rate type, basis, tiers and TOU windows can&apos;t be changed after creation -- delete and recreate the rate instead.</p>
          <ErrorText error={updateMutation.error} />
          <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Save</button>
        </form>
      ) : (
        <div className="space-y-3 text-sm">
          <p><span className="text-slate-400">Rate Type:</span> {rate.rate_type}</p>
          {rate.rate != null && <p><span className="text-slate-400">Rate:</span> ${rate.rate}</p>}
          {rate.basis && <p><span className="text-slate-400">Basis:</span> {rate.basis}</p>}
          {rate.tiers.length > 0 && (
            <div>
              <p className="mb-1 font-medium text-slate-700">Tiers</p>
              <table className="w-full text-sm">
                <tbody>
                  {rate.tiers.map((t) => (
                    <tr key={t.id} className="border-t border-slate-100">
                      <td className="py-1">{t.tier_from} – {t.tier_to ?? "∞"}</td>
                      <td className="py-1 text-right">${t.price}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {rate.tou_rates.length > 0 && (
            <div>
              <p className="mb-1 font-medium text-slate-700">Time-of-Use Windows</p>
              <table className="w-full text-sm">
                <tbody>
                  {rate.tou_rates.map((t) => (
                    <tr key={t.id} className="border-t border-slate-100">
                      <td className="py-1">{t.start_time} – {t.end_time}</td>
                      <td className="py-1 text-right">${t.price}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <ErrorText error={deleteMutation.error} />
          <div className="flex gap-2">
            <button onClick={() => setEditing(true)} className="flex-1 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Edit</button>
            <button
              onClick={() => { if (window.confirm(`Delete rate "${rate.name}"? This cannot be undone.`)) deleteMutation.mutate(); }}
              className="flex-1 rounded-md border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}

function RateBuilder() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [viewing, setViewing] = useState<RateOut | null>(null);
  const { register, control, handleSubmit, watch, reset, formState } = useForm<RateForm>({
    defaultValues: { rate_type: "fixed", tiers: [{ tier_from: 0, tier_to: null, price: 0 }], tou_rates: [{ start_time: "00:00", end_time: "12:00", price: 0 }] },
  });
  const rateType = watch("rate_type");
  const basis = watch("basis");
  const tiersArray = useFieldArray({ control, name: "tiers" });
  const touArray = useFieldArray({ control, name: "tou_rates" });

  const ratesQuery = useQuery({ queryKey: ["rates"], queryFn: async () => (await api.get<RateOut[]>("/rates")).data });

  const createMutation = useMutation({
    mutationFn: async (values: RateForm) => {
      const payload: Record<string, unknown> = { name: values.name, rate_type: values.rate_type };
      if (values.rate_type !== "variable") payload.rate = Number(values.rate);
      else {
        payload.basis = values.basis;
        if (values.basis === "tiered") payload.tiers = values.tiers.map((t) => ({ tier_from: Number(t.tier_from), tier_to: t.tier_to === null || (t.tier_to as unknown as string) === "" ? null : Number(t.tier_to), price: Number(t.price) }));
        if (values.basis === "time_of_use") payload.tou_rates = values.tou_rates.map((t) => ({ start_time: t.start_time, end_time: t.end_time, price: Number(t.price) }));
      }
      return (await api.post("/rates", payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rates"] });
      setOpen(false);
      reset();
    },
  });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-700">Rates</h2>
        <button onClick={() => setOpen(true)} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          + Add Rate
        </button>
      </div>
      {ratesQuery.isError ? (
        <ErrorText error={ratesQuery.error} />
      ) : (
        <DataTable<RateOut>
          columns={[
            { key: "name", label: "Name" },
            { key: "rate_type", label: "Type" },
            { key: "rate", label: "Rate", render: (r) => (r.rate != null ? `$${r.rate}` : `— (${r.basis})`) },
            { key: "id", label: "Action", render: (r) => <button onClick={() => setViewing(r)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View</button> },
          ]}
          rows={ratesQuery.data ?? []}
        />
      )}

      {viewing && <RateDetailModal rate={viewing} onClose={() => setViewing(null)} onDeleted={() => setViewing(null)} />}

      {open && (
        <Modal title="New Rate" onClose={() => setOpen(false)}>
          <form onSubmit={handleSubmit((v) => createMutation.mutate(v))} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Rate Name</label>
              <input {...register("name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Rate Type</label>
              <select {...register("rate_type")} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                <option value="fixed">Fixed</option>
                <option value="per_unit_area">Per Unit Area</option>
                <option value="variable">Variable</option>
              </select>
            </div>

            {rateType !== "variable" && (
              <div>
                <label className="block text-sm font-medium text-slate-700">Rate ($)</label>
                <input type="number" step="any" {...register("rate", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
            )}

            {rateType === "variable" && (
              <>
                <div>
                  <label className="block text-sm font-medium text-slate-700">Basis</label>
                  <select {...register("basis", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                    <option value="tiered">Tiered</option>
                    <option value="time_of_use">Time Of Use</option>
                  </select>
                </div>

                {basis === "tiered" && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-slate-700">Tiers</label>
                    {tiersArray.fields.map((f, i) => (
                      <div key={f.id} className="flex gap-2">
                        <input placeholder="From" type="number" step="any" {...register(`tiers.${i}.tier_from` as const)} className="w-1/4 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm" />
                        <input placeholder="To (blank=open)" type="number" step="any" {...register(`tiers.${i}.tier_to` as const)} className="w-1/3 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm" />
                        <input placeholder="Price" type="number" step="any" {...register(`tiers.${i}.price` as const)} className="w-1/4 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm" />
                        <button type="button" onClick={() => tiersArray.remove(i)} className="text-slate-400 hover:text-red-600">✕</button>
                      </div>
                    ))}
                    <button type="button" onClick={() => tiersArray.append({ tier_from: 0, tier_to: null, price: 0 })} className="text-xs font-medium text-slate-600 underline">
                      + Add tier
                    </button>
                  </div>
                )}

                {basis === "time_of_use" && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-slate-700">Time-of-Use Windows</label>
                    {touArray.fields.map((f, i) => (
                      <div key={f.id} className="flex gap-2">
                        <input type="time" {...register(`tou_rates.${i}.start_time` as const)} className="w-1/3 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm" />
                        <input type="time" {...register(`tou_rates.${i}.end_time` as const)} className="w-1/3 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm" />
                        <input placeholder="Price" type="number" step="any" {...register(`tou_rates.${i}.price` as const)} className="w-1/4 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm" />
                        <button type="button" onClick={() => touArray.remove(i)} className="text-slate-400 hover:text-red-600">✕</button>
                      </div>
                    ))}
                    <button type="button" onClick={() => touArray.append({ start_time: "00:00", end_time: "12:00", price: 0 })} className="text-xs font-medium text-slate-600 underline">
                      + Add window
                    </button>
                  </div>
                )}
              </>
            )}

            <ErrorText error={createMutation.error} />
            <button type="submit" disabled={formState.isSubmitting} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              Save Rate
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

export default function AccountPage() {
  return (
    <PageShell title="Categories & Rates">
      <div className="space-y-10">
        <SimpleCrud
          resourceKey="categories" endpoint="/categories" title="Categories"
          fields={[{ name: "name", label: "Name", type: "text", required: true }]}
          columns={[{ key: "name", label: "Name" }]}
        />
        <SimpleCrud
          resourceKey="sub-categories" endpoint="/sub-categories" title="Sub-Categories"
          fields={[
            { name: "category_id", label: "Category", type: "select", required: true, optionsEndpoint: "/categories" },
            { name: "name", label: "Name", type: "text", required: true },
          ]}
          columns={[{ key: "name", label: "Name" }, { key: "category_id", label: "Category" }]}
        />
        <RateBuilder />
        <SimpleCrud
          resourceKey="service-charges" endpoint="/service-charges" title="Service Charges"
          fields={[
            { name: "name", label: "Name", type: "text", required: true },
            { name: "utility_service_id", label: "Utility Service (blank = All)", type: "select", optionsEndpoint: "/services/catalogue", readOnlyOnEdit: true },
            { name: "charge_type", label: "Type", type: "select", required: true, options: [{ value: "fixed", label: "Fixed" }, { value: "variable", label: "Variable" }], readOnlyOnEdit: true },
            { name: "rate", label: "Rate ($)", type: "number", required: true },
          ]}
          columns={[{ key: "name", label: "Name" }, { key: "charge_type", label: "Type" }, { key: "rate", label: "Rate" }]}
        />
      </div>
    </PageShell>
  );
}
