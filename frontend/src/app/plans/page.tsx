"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { Modal } from "@/components/Modal";
import { api } from "@/lib/api";
import type { CategoryOut, PlanOut, RateOut, SubCategoryOut, UtilityServiceOut } from "@/lib/types";

interface PlanForm {
  name: string;
  category_id: string;
  sub_category_id: string;
  tax_percent?: number;
  billing_frequency: string;
  components: { utility_service_id: string; rate_id: string }[];
}

function PlanDetailModal({
  plan, categories, subCategories, services, rates, onClose,
}: {
  plan: PlanOut; categories?: CategoryOut[]; subCategories?: SubCategoryOut[]; services?: UtilityServiceOut[]; rates?: RateOut[]; onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const { register, handleSubmit, reset } = useForm<{ name: string; tax_percent?: number; billing_frequency: string; is_active: boolean }>();

  useEffect(() => {
    reset({ name: plan.name, tax_percent: plan.tax_percent ?? undefined, billing_frequency: plan.billing_frequency ?? "monthly", is_active: plan.is_active });
  }, [plan, reset]);

  const updateMutation = useMutation({
    mutationFn: async (values: { name: string; tax_percent?: number; billing_frequency: string; is_active: boolean }) =>
      (await api.patch(`/plans/${plan.id}`, { ...values, tax_percent: values.tax_percent ? Number(values.tax_percent) : undefined })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      onClose();
    },
  });

  const nameFor = (list: { id: string; name: string }[] | undefined, id: string) => list?.find((x) => x.id === id)?.name ?? id;

  return (
    <Modal title={editing ? `Edit ${plan.name}` : plan.name} onClose={onClose}>
      {editing ? (
        <form onSubmit={handleSubmit((v) => updateMutation.mutate(v))} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Plan Name</label>
            <input {...register("name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Tax %</label>
            <input type="number" step="any" {...register("tax_percent")} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Billing Frequency</label>
            <select {...register("billing_frequency")} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
              <option value="monthly">Monthly</option>
              <option value="bi_monthly">Bi-monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="annually">Annually</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" {...register("is_active")} className="h-4 w-4" /> Active
          </label>
          <p className="text-xs text-slate-400">Category, sub-category and service components can&apos;t be changed after creation.</p>
          <ErrorText error={updateMutation.error} />
          <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Save</button>
        </form>
      ) : (
        <div className="space-y-3 text-sm">
          <p><span className="text-slate-400">Category:</span> {nameFor(categories, plan.category_id)}</p>
          <p><span className="text-slate-400">Sub-Category:</span> {nameFor(subCategories, plan.sub_category_id)}</p>
          <p><span className="text-slate-400">Tax %:</span> {plan.tax_percent ?? "—"}</p>
          <p><span className="text-slate-400">Billing Frequency:</span> {plan.billing_frequency ?? "—"}</p>
          <p><span className="text-slate-400">Status:</span> <StatusBadge status={plan.is_active ? "Active" : "Inactive"} tone={plan.is_active ? "green" : "slate"} /></p>
          <div>
            <p className="mb-1 font-medium text-slate-700">Components</p>
            <table className="w-full text-sm">
              <tbody>
                {plan.components.map((c) => (
                  <tr key={c.id} className="border-t border-slate-100">
                    <td className="py-1">{nameFor(services, c.utility_service_id)}</td>
                    <td className="py-1 text-right">{nameFor(rates, c.rate_id)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button onClick={() => setEditing(true)} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Edit</button>
        </div>
      )}
    </Modal>
  );
}

export default function PlansPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [viewing, setViewing] = useState<PlanOut | null>(null);
  const { register, control, handleSubmit, reset, formState } = useForm<PlanForm>({
    defaultValues: { billing_frequency: "monthly", components: [{ utility_service_id: "", rate_id: "" }] },
  });
  const componentsArray = useFieldArray({ control, name: "components" });

  const plansQuery = useQuery({ queryKey: ["plans"], queryFn: async () => (await api.get<PlanOut[]>("/plans")).data });
  const categoriesQuery = useQuery({ queryKey: ["categories"], queryFn: async () => (await api.get<CategoryOut[]>("/categories")).data });
  const subCategoriesQuery = useQuery({ queryKey: ["sub-categories"], queryFn: async () => (await api.get<SubCategoryOut[]>("/sub-categories")).data });
  const servicesQuery = useQuery({ queryKey: ["/services/catalogue"], queryFn: async () => (await api.get<UtilityServiceOut[]>("/services/catalogue")).data });
  const ratesQuery = useQuery({ queryKey: ["rates"], queryFn: async () => (await api.get<RateOut[]>("/rates")).data });

  const createMutation = useMutation({
    mutationFn: async (values: PlanForm) => {
      const payload = {
        ...values,
        tax_percent: values.tax_percent ? Number(values.tax_percent) : undefined,
        components: values.components.filter((c) => c.utility_service_id && c.rate_id),
      };
      return (await api.post("/plans", payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      setOpen(false);
      reset();
    },
  });

  return (
    <PageShell title="Plans">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-700">Plans</h2>
        <button onClick={() => setOpen(true)} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          + Add Plan
        </button>
      </div>

      {plansQuery.isError ? (
        <ErrorText error={plansQuery.error} />
      ) : (
        <DataTable<PlanOut>
          columns={[
            { key: "name", label: "Name" },
            { key: "billing_frequency", label: "Frequency" },
            { key: "tax_percent", label: "Tax %" },
            { key: "components", label: "Components", render: (p) => `${p.components.length} service(s)` },
            { key: "id", label: "Action", render: (p) => <button onClick={() => setViewing(p)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View</button> },
          ]}
          rows={plansQuery.data ?? []}
        />
      )}

      {viewing && (
        <PlanDetailModal
          plan={viewing} categories={categoriesQuery.data} subCategories={subCategoriesQuery.data}
          services={servicesQuery.data} rates={ratesQuery.data} onClose={() => setViewing(null)}
        />
      )}

      {open && (
        <Modal title="New Plan" onClose={() => setOpen(false)}>
          <form onSubmit={handleSubmit((v) => createMutation.mutate(v))} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Plan Name</label>
              <input {...register("name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Category</label>
                <select {...register("category_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                  <option value="">Select…</option>
                  {categoriesQuery.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Sub-Category</label>
                <select {...register("sub_category_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                  <option value="">Select…</option>
                  {subCategoriesQuery.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Tax %</label>
                <input type="number" step="any" {...register("tax_percent")} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Billing Frequency</label>
                <select {...register("billing_frequency")} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                  <option value="monthly">Monthly</option>
                  <option value="bi_monthly">Bi-monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="annually">Annually</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">Service Components (Service → Rate)</label>
              {componentsArray.fields.map((f, i) => (
                <div key={f.id} className="flex gap-2">
                  <select {...register(`components.${i}.utility_service_id` as const)} className="w-1/2 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm">
                    <option value="">Service…</option>
                    {servicesQuery.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                  <select {...register(`components.${i}.rate_id` as const)} className="w-1/2 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1.5 text-sm">
                    <option value="">Rate…</option>
                    {ratesQuery.data?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                  <button type="button" onClick={() => componentsArray.remove(i)} className="text-slate-400 hover:text-red-600">✕</button>
                </div>
              ))}
              <button type="button" onClick={() => componentsArray.append({ utility_service_id: "", rate_id: "" })} className="text-xs font-medium text-slate-600 underline">
                + Add component
              </button>
            </div>

            <ErrorText error={createMutation.error} />
            <button type="submit" disabled={formState.isSubmitting} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              Save Plan
            </button>
          </form>
        </Modal>
      )}
    </PageShell>
  );
}
