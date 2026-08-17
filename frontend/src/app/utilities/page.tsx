"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { Modal } from "@/components/Modal";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { api } from "@/lib/api";

interface Tenant {
  id: string;
  name: string;
  status: string;
  email: string | null;
  phone_no: string | null;
  address?: string | null;
  website?: string | null;
  currency?: string | null;
  timezone?: string | null;
  date_format?: string | null;
  e_transfer?: string | null;
  hst_gst_no?: string | null;
}

interface OnboardForm {
  name: string;
  phone_no: string;
  address: string;
  website: string;
  email: string;
  currency: string;
  timezone: string;
  date_format: string;
  admin_full_name: string;
  admin_email: string;
}

type TenantForm = Omit<OnboardForm, "admin_full_name" | "admin_email"> & { e_transfer?: string; hst_gst_no?: string };

const TENANT_FIELDS: [keyof TenantForm, string][] = [
  ["name", "Utility Name"], ["phone_no", "Phone No (+E.164)"], ["address", "Address"], ["website", "Website (https://...)"],
  ["email", "Email"], ["currency", "Currency"], ["timezone", "Time Zone"], ["date_format", "Date Format"],
  ["e_transfer", "E-Transfer"], ["hst_gst_no", "GST/HST No"],
];

function TenantDetailModal({ tenant, onClose }: { tenant: Tenant; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const { register, handleSubmit, reset } = useForm<TenantForm>();

  useEffect(() => {
    reset({
      name: tenant.name, phone_no: tenant.phone_no ?? "", address: tenant.address ?? "", website: tenant.website ?? "",
      email: tenant.email ?? "", currency: tenant.currency ?? "", timezone: tenant.timezone ?? "", date_format: tenant.date_format ?? "",
      e_transfer: tenant.e_transfer ?? "", hst_gst_no: tenant.hst_gst_no ?? "",
    });
  }, [tenant, reset]);

  const updateMutation = useMutation({
    mutationFn: async (values: TenantForm) => (await api.patch(`/admin/tenants/${tenant.id}`, values)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tenants"] });
      onClose();
    },
  });

  return (
    <Modal title={editing ? `Edit ${tenant.name}` : tenant.name} onClose={onClose}>
      <form onSubmit={handleSubmit((v) => updateMutation.mutate(v))} className="space-y-3">
        {TENANT_FIELDS.map(([name, label]) => (
          <div key={name}>
            <label className="block text-sm font-medium text-slate-700">{label}</label>
            {editing ? (
              <input {...register(name, { required: name === "name" })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            ) : (
              <p className="mt-1 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-800">{(tenant as unknown as Record<string, string | null | undefined>)[name] || "—"}</p>
            )}
          </div>
        ))}
        {editing ? (
          <>
            <ErrorText error={updateMutation.error} />
            <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Save</button>
          </>
        ) : (
          <button type="button" onClick={() => setEditing(true)} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Edit</button>
        )}
      </form>
    </Modal>
  );
}

export default function UtilitiesPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [viewing, setViewing] = useState<Tenant | null>(null);
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null);
  const { register, handleSubmit, reset, formState } = useForm<OnboardForm>({
    defaultValues: { currency: "USD", timezone: "America/New_York", date_format: "MM/DD/YYYY" },
  });

  const tenantsQuery = useQuery({ queryKey: ["admin-tenants"], queryFn: async () => (await api.get<Tenant[]>("/admin/tenants")).data });

  const onboardMutation = useMutation({
    mutationFn: async (values: OnboardForm) => (await api.post("/admin/tenants", values)).data,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["admin-tenants"] });
      setCredentials({ email: data.admin_email, password: data.temp_password });
      setOpen(false);
      reset();
    },
  });

  const statusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => (await api.post(`/admin/tenants/${id}/status`, { status })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-tenants"] }),
  });

  return (
    <PageShell title="Utilities">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-700">All Utilities</h2>
        <button onClick={() => setOpen(true)} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          + Onboard Utility
        </button>
      </div>

      {statusMutation.isError && <div className="mb-4"><ErrorText error={statusMutation.error} /></div>}
      {tenantsQuery.isError && <div className="mb-4"><ErrorText error={tenantsQuery.error} /></div>}

      <DataTable<Tenant>
        columns={[
          { key: "name", label: "Name" },
          { key: "email", label: "Email" },
          { key: "phone_no", label: "Phone" },
          {
            key: "status",
            label: "Status",
            render: (t) => <StatusBadge status={t.status} tone={t.status === "active" ? "green" : "amber"} />,
          },
          {
            key: "id",
            label: "Action",
            render: (t) => (
              <div className="flex gap-3">
                <button onClick={() => setViewing(t)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View</button>
                <button
                  onClick={() => statusMutation.mutate({ id: t.id, status: t.status === "active" ? "suspended" : "active" })}
                  className="text-xs font-medium text-slate-600 underline hover:text-slate-900"
                >
                  {t.status === "active" ? "Suspend" : "Activate"}
                </button>
              </div>
            ),
          },
        ]}
        rows={tenantsQuery.data ?? []}
      />

      {viewing && <TenantDetailModal tenant={viewing} onClose={() => setViewing(null)} />}

      {open && (
        <Modal title="Onboard Utility" onClose={() => setOpen(false)}>
          <form onSubmit={handleSubmit((v) => onboardMutation.mutate(v))} className="space-y-3">
            {[
              ["name", "Utility Name"], ["phone_no", "Phone No (+E.164)"], ["address", "Address"], ["website", "Website (https://...)"],
              ["email", "Email"], ["currency", "Currency"], ["timezone", "Time Zone"], ["date_format", "Date Format"],
              ["admin_full_name", "Utility Admin Name"], ["admin_email", "Utility Admin Email"],
            ].map(([name, label]) => (
              <div key={name}>
                <label className="block text-sm font-medium text-slate-700">{label}</label>
                <input {...register(name as keyof OnboardForm, { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
            ))}
            <ErrorText error={onboardMutation.error} />
            <button type="submit" disabled={formState.isSubmitting} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              Create Utility
            </button>
          </form>
        </Modal>
      )}

      {credentials && (
        <Modal title="Utility Admin Credentials" onClose={() => setCredentials(null)}>
          <p className="text-sm text-slate-600">Share these with the new Utility Admin (one-time only, not emailed):</p>
          <div className="mt-3 rounded-md bg-slate-50 p-3 text-sm">
            <p><span className="text-slate-400">Email:</span> {credentials.email}</p>
            <p><span className="text-slate-400">Temp password:</span> {credentials.password}</p>
          </div>
        </Modal>
      )}
    </PageShell>
  );
}
