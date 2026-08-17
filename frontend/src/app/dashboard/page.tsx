"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { PageShell } from "@/components/PageShell";
import { StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { api } from "@/lib/api";
import { fetchMe, isAuthenticated } from "@/lib/auth";

interface Tenant {
  id: string;
  name: string;
  status: string;
  email: string | null;
}

interface SuperAdminDashboard {
  total_utilities: number;
  active_utilities: number;
  suspended_utilities: number;
  total_consumers: number;
  total_meters: number;
  bills_generated: number;
  failed_jobs: number;
  active_users: number;
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const meQuery = useQuery({ queryKey: ["me"], queryFn: fetchMe, enabled: isAuthenticated() });
  const me = meQuery.data;
  const isConsumer = me?.roles.some((r) => r.name === "Consumer") && !me?.is_superadmin;

  useEffect(() => {
    if (isConsumer) router.replace("/portal");
  }, [isConsumer, router]);

  const statsQuery = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: async () => (await api.get<SuperAdminDashboard>("/admin/dashboard")).data,
    enabled: !!me?.is_superadmin,
  });
  const tenantsQuery = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: async () => (await api.get<Tenant[]>("/admin/tenants")).data,
    enabled: !!me?.is_superadmin,
  });
  const tenantQuery = useQuery({
    queryKey: ["tenant-current"],
    queryFn: async () => (await api.get<Tenant>("/tenants/current")).data,
    enabled: !!me && !me.is_superadmin && !isConsumer,
  });

  if (isConsumer) return null; // redirecting to /portal

  return (
    <PageShell title="Dashboard">
      {me?.is_superadmin ? (
        <div className="space-y-6">
          {(statsQuery.isError || tenantsQuery.isError) && <ErrorText error={statsQuery.error ?? tenantsQuery.error} />}
          {statsQuery.data && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard label="Utilities" value={statsQuery.data.total_utilities} />
              <StatCard label="Active" value={statsQuery.data.active_utilities} />
              <StatCard label="Suspended" value={statsQuery.data.suspended_utilities} />
              <StatCard label="Active Users" value={statsQuery.data.active_users} />
              <StatCard label="Consumers" value={statsQuery.data.total_consumers} />
              <StatCard label="Meters" value={statsQuery.data.total_meters} />
              <StatCard label="Bills Generated" value={statsQuery.data.bills_generated} />
              <StatCard label="Failed Bill Runs" value={statsQuery.data.failed_jobs} />
            </div>
          )}
          <div>
            <h2 className="mb-3 text-sm font-medium text-slate-700">Utilities</h2>
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-4 py-2 font-medium">Name</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium">Email</th>
                  </tr>
                </thead>
                <tbody>
                  {tenantsQuery.data?.map((t) => (
                    <tr key={t.id} className="border-t border-slate-100">
                      <td className="px-4 py-2">{t.name}</td>
                      <td className="px-4 py-2">
                        <StatusBadge status={t.status} tone={t.status === "active" ? "green" : "amber"} />
                      </td>
                      <td className="px-4 py-2 text-slate-500">{t.email ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          {tenantQuery.isError && <ErrorText error={tenantQuery.error} />}
          <p className="font-medium text-slate-900">{tenantQuery.data?.name ?? "Loading..."}</p>
          <p className="mt-1 text-slate-500">{tenantQuery.data?.email}</p>
          <p className="mt-1 text-slate-500">Status: {tenantQuery.data?.status}</p>
          <p className="mt-4 text-slate-400">Use the sidebar to manage territory, rates, consumers, meters, readings, VEE and billing.</p>
        </div>
      )}
    </PageShell>
  );
}
