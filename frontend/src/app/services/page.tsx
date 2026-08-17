"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageShell } from "@/components/PageShell";
import { ErrorText } from "@/components/ErrorText";
import { api } from "@/lib/api";
import type { TenantServiceOut } from "@/lib/types";

export default function ServicesPage() {
  const queryClient = useQueryClient();
  const servicesQuery = useQuery({ queryKey: ["tenant-services"], queryFn: async () => (await api.get<TenantServiceOut[]>("/services/tenant")).data });

  const toggleMutation = useMutation({
    mutationFn: async (payload: { utility_service_id: string; is_enabled: boolean }) => (await api.put("/services/tenant", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenant-services"] }),
  });

  return (
    <PageShell title="Utility Services">
      <p className="mb-4 text-sm text-slate-500">Toggle which utility services this tenant offers. Nothing else in the app hard-codes these names.</p>

      {servicesQuery.isError && <div className="mb-4 max-w-md"><ErrorText error={servicesQuery.error} /></div>}
      {toggleMutation.isError && <div className="mb-4 max-w-md"><ErrorText error={toggleMutation.error} /></div>}

      {servicesQuery.isLoading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : (
        <div className="grid max-w-md gap-3">
          {servicesQuery.data?.map((svc) => (
            <label key={svc.utility_service_id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3">
              <span className="text-sm font-medium text-slate-800">{svc.name}</span>
              <input
                type="checkbox"
                checked={svc.is_enabled}
                onChange={(e) => toggleMutation.mutate({ utility_service_id: svc.utility_service_id, is_enabled: e.target.checked })}
                className="h-5 w-5"
              />
            </label>
          ))}
        </div>
      )}
    </PageShell>
  );
}
