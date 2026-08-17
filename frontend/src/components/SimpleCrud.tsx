"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "@/lib/api";
import { Column, DataTable } from "./DataTable";
import { ErrorText } from "./ErrorText";
import { Modal } from "./Modal";

export interface FieldOption {
  value: string;
  label: string;
}

export interface FieldDef {
  name: string;
  label: string;
  type: "text" | "number" | "date" | "checkbox" | "select" | "multiselect";
  required?: boolean;
  options?: FieldOption[];
  optionsEndpoint?: string; // fetched at render time, maps {id,name} -> options
  readOnlyOnEdit?: boolean; // shown but disabled once a record exists (e.g. a parent link that drives auto-assignment)
}

type PanelState = { mode: "create" } | { mode: "view" | "edit"; row: Record<string, unknown> } | null;

/**
 * Reusable list+create+view+edit+delete screen for the ~15 flat CRUD
 * entities (Territory levels, Categories, Service Charges, VEE
 * rules/configs, Bill Cycles, ...) -- CLAUDE.md §29: "reusable DataTable /
 * reusable form components" and "Every CRUD page needs: list, create,
 * edit, view, delete/deactivate". Entities with nested data or business
 * logic (Rate, Plan, Consumer, Meter Reading, Bill Run) get hand-built
 * pages instead.
 */
export function SimpleCrud<T extends { id: string }>({
  resourceKey,
  endpoint,
  title,
  fields,
  columns,
  extraPayload,
  canDelete = true,
}: {
  resourceKey: string;
  endpoint: string;
  title: string;
  fields: FieldDef[];
  columns: Column<T>[];
  extraPayload?: Record<string, unknown>;
  canDelete?: boolean;
}) {
  const queryClient = useQueryClient();
  const [panel, setPanel] = useState<PanelState>(null);
  const { register, handleSubmit, reset, formState } = useForm<Record<string, unknown>>();

  const listQuery = useQuery({ queryKey: [resourceKey], queryFn: async () => (await api.get<T[]>(endpoint)).data });

  // Fetched unconditionally (not just while a modal is open) so the list
  // table can resolve foreign-key columns to names too -- see tableColumns
  // below. These are small lookup lists (regions, categories, ...), so the
  // extra always-on requests are cheap.
  const optionQueries = fields
    .filter((f) => f.optionsEndpoint)
    .map((f) => ({
      field: f,
      query: useQuery({
        queryKey: [f.optionsEndpoint],
        queryFn: async () => (await api.get<{ id: string; name: string }[]>(f.optionsEndpoint as string)).data,
      }),
    }));

  const optionsFor = (field: FieldDef) => field.options ?? optionQueries.find((q) => q.field.name === field.name)?.query.data?.map((o) => ({ value: o.id, label: o.name })) ?? [];
  const labelFor = (field: FieldDef, rawValue: unknown) => {
    if (field.type === "select") return optionsFor(field).find((o) => o.value === rawValue)?.label ?? String(rawValue ?? "—");
    if (field.type === "multiselect") return Array.isArray(rawValue) && rawValue.length ? rawValue.map((v) => optionsFor(field).find((o) => o.value === v)?.label ?? v).join(", ") : "—";
    if (field.type === "checkbox") return rawValue ? "Yes" : "No";
    return rawValue === null || rawValue === undefined || rawValue === "" ? "—" : String(rawValue);
  };

  useEffect(() => {
    if (panel?.mode === "edit" || panel?.mode === "view") {
      const initial: Record<string, unknown> = {};
      for (const field of fields) {
        const value = panel.row[field.name];
        initial[field.name] = field.type === "multiselect" && Array.isArray(value) ? value[0] : value;
      }
      reset(initial);
    } else if (panel?.mode === "create") {
      reset({});
    }
  }, [panel, fields, reset]);

  function buildPayload(values: Record<string, unknown>) {
    const payload: Record<string, unknown> = { ...extraPayload };
    for (const field of fields) {
      const raw = values[field.name];
      if (field.type === "number") payload[field.name] = raw === "" || raw === undefined ? undefined : Number(raw);
      else if (field.type === "checkbox") payload[field.name] = Boolean(raw);
      else if (field.type === "multiselect") payload[field.name] = raw ? [raw] : [];
      else payload[field.name] = raw === "" ? undefined : raw;
    }
    return payload;
  }

  const createMutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => (await api.post(endpoint, buildPayload(values))).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [resourceKey] });
      setPanel(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      if (panel?.mode !== "edit") return;
      return (await api.patch(`${endpoint}/${panel.row.id}`, buildPayload(values))).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [resourceKey] });
      setPanel(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => api.delete(`${endpoint}/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [resourceKey] });
      setPanel(null);
    },
  });

  // Auto-resolve any caller-supplied column that names a select/multiselect
  // field with an optionsEndpoint (e.g. "category_id") to its label instead
  // of the raw id -- unless the caller already gave it a custom `render`.
  // This is what keeps every SimpleCrud table (Territory's 9 levels,
  // Sub-Categories, VEE Config/Schedule, Bill Schedules, ...) showing
  // names instead of UUIDs without every page having to resolve it by hand.
  const resolvedColumns: Column<T>[] = columns.map((col) => {
    if (col.render) return col;
    const field = fields.find((f) => f.name === col.key && f.optionsEndpoint);
    if (!field) return col;
    return { ...col, render: (row) => labelFor(field, (row as Record<string, unknown>)[col.key as string]) };
  });

  const tableColumns: Column<T>[] = [
    ...resolvedColumns,
    {
      key: "id",
      label: "Action",
      render: (row) => (
        <div className="flex gap-3">
          <button onClick={() => setPanel({ mode: "view", row: row as unknown as Record<string, unknown> })} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">
            View
          </button>
          <button onClick={() => setPanel({ mode: "edit", row: row as unknown as Record<string, unknown> })} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">
            Edit
          </button>
          {canDelete && (
            <button
              onClick={() => {
                if (window.confirm(`Delete this ${title.replace(/s$/, "")}? This cannot be undone.`)) deleteMutation.mutate(row.id);
              }}
              className="text-xs font-medium text-red-600 underline hover:text-red-800"
            >
              Delete
            </button>
          )}
        </div>
      ),
    },
  ];

  const isView = panel?.mode === "view";

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-700">{title}</h2>
        <button onClick={() => setPanel({ mode: "create" })} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          + Add
        </button>
      </div>

      {listQuery.isLoading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : listQuery.isError ? (
        <ErrorText error={listQuery.error} />
      ) : (
        <DataTable columns={tableColumns} rows={listQuery.data ?? []} />
      )}
      {deleteMutation.isError && <div className="mt-3"><ErrorText error={deleteMutation.error} /></div>}

      {panel && (
        <Modal title={panel.mode === "create" ? `New ${title}` : panel.mode === "view" ? `View ${title}` : `Edit ${title}`} onClose={() => setPanel(null)}>
          <form
            onSubmit={handleSubmit((values) => (panel.mode === "edit" ? updateMutation.mutate(values) : createMutation.mutate(values)))}
            className="space-y-3"
          >
            {fields.map((field) => (
              <div key={field.name}>
                <label className="block text-sm font-medium text-slate-700">{field.label}</label>
                {isView ? (
                  <p className="mt-1 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-800">{labelFor(field, panel.row[field.name])}</p>
                ) : field.type === "select" || field.type === "multiselect" ? (
                  <select
                    {...register(field.name, { required: field.required })}
                    disabled={panel.mode === "edit" && field.readOnlyOnEdit}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-400"
                  >
                    <option value="">Select…</option>
                    {optionsFor(field).map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === "checkbox" ? (
                  <input type="checkbox" {...register(field.name)} className="mt-1 h-4 w-4" />
                ) : (
                  <input
                    type={field.type}
                    step={field.type === "number" ? "any" : undefined}
                    disabled={panel.mode === "edit" && field.readOnlyOnEdit}
                    {...register(field.name, { required: field.required })}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-400"
                  />
                )}
              </div>
            ))}

            {isView ? (
              <button type="button" onClick={() => setPanel({ mode: "edit", row: panel.row })} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
                Edit
              </button>
            ) : (
              <>
                <ErrorText error={panel.mode === "edit" ? updateMutation.error : createMutation.error} />
                <button
                  type="submit"
                  disabled={formState.isSubmitting || createMutation.isPending || updateMutation.isPending}
                  className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
                >
                  Save
                </button>
              </>
            )}
          </form>
        </Modal>
      )}
    </div>
  );
}
