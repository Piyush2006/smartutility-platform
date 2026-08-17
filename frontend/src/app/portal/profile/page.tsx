"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { ErrorText } from "@/components/ErrorText";
import { StatusBadge } from "@/components/DataTable";
import { api } from "@/lib/api";
import type { ConsumerOut, MeterOut } from "@/lib/types";

interface PortalPlan {
  id: string;
  name: string;
  billing_frequency: string | null;
  tax_percent: number | null;
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-2 text-sm last:border-0">
      <span className="text-slate-400">{label}</span>
      <span className="font-medium text-slate-800">{value ?? "—"}</span>
    </div>
  );
}

export default function PortalProfilePage() {
  const queryClient = useQueryClient();
  const profileQuery = useQuery({ queryKey: ["portal-profile"], queryFn: async () => (await api.get<ConsumerOut>("/portal/profile")).data });
  const meterQuery = useQuery({ queryKey: ["portal-meter"], queryFn: async () => (await api.get<MeterOut>("/portal/meter")).data });
  const planQuery = useQuery({ queryKey: ["portal-plan"], queryFn: async () => (await api.get<PortalPlan>("/portal/plan")).data });

  const { register, handleSubmit, reset, formState } = useForm<{ contact_no: string; billing_address: string }>();

  useEffect(() => {
    if (profileQuery.data) reset({ contact_no: profileQuery.data.contact_no, billing_address: profileQuery.data.billing_address });
  }, [profileQuery.data, reset]);

  const updateMutation = useMutation({
    mutationFn: async (values: { contact_no: string; billing_address: string }) => (await api.patch("/portal/profile", values)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["portal-profile"] }),
  });

  const p = profileQuery.data;
  const m = meterQuery.data;
  const plan = planQuery.data;

  return (
    <PageShell title="My Profile">
      {profileQuery.isError && <ErrorText error={profileQuery.error} />}
      {p && (
        <div className="grid max-w-4xl gap-6 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-700">Account</h2>
              <StatusBadge status={p.status} tone={p.status === "active" ? "green" : "slate"} />
            </div>
            <InfoRow label="Name" value={p.full_name} />
            <InfoRow label="Email" value={p.email_address} />
            <InfoRow label="Contact No" value={p.contact_no} />
            <InfoRow label="Activation Date" value={p.activation_date} />
            <InfoRow label="First Meter Reading" value={`${p.first_meter_reading} (on ${p.first_meter_reading_date})`} />
            <p className="mt-2 text-xs text-slate-400">Name and email are managed by your utility -- contact support to change them.</p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-medium text-slate-700">Plan &amp; Meter</h2>
            <InfoRow label="Plan" value={plan?.name} />
            <InfoRow label="Billing Frequency" value={plan?.billing_frequency} />
            <InfoRow label="Tax %" value={plan?.tax_percent != null ? `${plan.tax_percent}%` : undefined} />
            <InfoRow label="Meter No" value={m?.meter_no} />
            <InfoRow label="Device No" value={m?.device_no} />
            <InfoRow label="Read Type" value={m?.read_type} />
            {meterQuery.isError && <ErrorText error={meterQuery.error} />}
            {planQuery.isError && <ErrorText error={planQuery.error} />}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 md:col-span-2">
            <h2 className="mb-3 text-sm font-medium text-slate-700">Service Address</h2>
            <InfoRow label="Service Address" value={p.service_address} />
          </div>

          <form onSubmit={handleSubmit((v) => updateMutation.mutate(v))} className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 md:col-span-2">
            <h2 className="text-sm font-medium text-slate-700">Editable Details</h2>
            <div>
              <label className="block text-sm font-medium text-slate-700">Contact No</label>
              <input {...register("contact_no", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Billing Address</label>
              <input {...register("billing_address", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <ErrorText error={updateMutation.error} />
            <button type="submit" disabled={formState.isSubmitting} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              Save Changes
            </button>
            {updateMutation.isSuccess && <p className="text-sm text-emerald-600">Saved.</p>}
          </form>
        </div>
      )}
    </PageShell>
  );
}
