"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageShell } from "@/components/PageShell";
import { SimpleCrud } from "@/components/SimpleCrud";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { api } from "@/lib/api";
import type { MeterOut, MeterRunOut, MeterScheduleOut } from "@/lib/types";

const TABS = ["Meters", "Routes", "Read Cycles", "Schedules", "Meter Runs"] as const;

function MeterSchedulesTab() {
  const queryClient = useQueryClient();
  const schedulesQuery = useQuery({ queryKey: ["meter-schedules"], queryFn: async () => (await api.get<MeterScheduleOut[]>("/meter-schedules")).data });
  const generateMutation = useMutation({
    mutationFn: async (id: string) => (await api.post(`/meter-schedules/${id}/generate-run`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["meter-runs"] }),
  });

  return (
    <div className="space-y-6">
      {generateMutation.isError && <ErrorText error={generateMutation.error} />}
      <SimpleCrud<MeterScheduleOut>
        resourceKey="meter-schedules" endpoint="/meter-schedules" title="Meter Schedules" canDelete={false}
        fields={[
          { name: "read_cycle_id", label: "Cycle Name", type: "select", required: true, optionsEndpoint: "/read-cycles", readOnlyOnEdit: true },
          { name: "recurring", label: "Recurring", type: "checkbox", readOnlyOnEdit: true },
          { name: "frequency", label: "Frequency", type: "select", options: [{ value: "Daily", label: "Daily" }, { value: "Weekly", label: "Weekly" }, { value: "Monthly", label: "Monthly" }, { value: "Quarterly", label: "Quarterly" }], readOnlyOnEdit: true },
          { name: "start_date", label: "Start Date", type: "date", required: true, readOnlyOnEdit: true },
          { name: "due_days", label: "Due Days", type: "number", readOnlyOnEdit: true },
          { name: "is_active", label: "Active", type: "checkbox" },
          { name: "description", label: "Description", type: "text" },
        ]}
        columns={[
          { key: "read_cycle_id", label: "Cycle" },
          { key: "start_date", label: "Start Date" },
          { key: "recurring", label: "Recurring", render: (s) => (s.recurring ? "Yes" : "No") },
          { key: "is_active", label: "Active", render: (s) => <StatusBadge status={s.is_active ? "Active" : "Inactive"} tone={s.is_active ? "green" : "slate"} /> },
          {
            key: "generate", label: "",
            render: (s) => (
              <button onClick={() => generateMutation.mutate(s.id)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">
                Generate Run
              </button>
            ),
          },
        ]}
      />
      {schedulesQuery.data?.length === 0 && <p className="text-sm text-slate-400">Create a Read Cycle first, then a Schedule.</p>}
    </div>
  );
}

function MeterRunsTab() {
  const runsQuery = useQuery({ queryKey: ["meter-runs"], queryFn: async () => (await api.get<MeterRunOut[]>("/meter-runs")).data });
  if (runsQuery.isError) return <ErrorText error={runsQuery.error} />;
  return (
    <DataTable<MeterRunOut>
      columns={[
        { key: "run_date", label: "Run Date" },
        { key: "premise_count", label: "Premises" },
        { key: "meter_count", label: "Meters" },
        { key: "readings_received", label: "Readings Received" },
        { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} tone={r.status === "completed" ? "green" : "amber"} /> },
      ]}
      rows={runsQuery.data ?? []}
      emptyLabel="No meter runs yet -- generate one from the Schedules tab."
    />
  );
}

export default function MetersPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Meters");

  return (
    <PageShell title="Meters & Routes">
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

      {tab === "Meters" && (
        <SimpleCrud<MeterOut>
          resourceKey="meters" endpoint="/meters" title="Meters" canDelete={false}
          fields={[
            { name: "meter_no", label: "Meter No", type: "text", required: true },
            { name: "device_no", label: "Device No", type: "text", required: true },
            { name: "utility_service_id", label: "Utility Service", type: "select", required: true, optionsEndpoint: "/services/catalogue", readOnlyOnEdit: true },
            { name: "read_type", label: "Read Type", type: "select", required: true, options: [{ value: "Manual", label: "Manual" }, { value: "Smart", label: "Smart" }, { value: "Photo", label: "Photo" }] },
            { name: "premise_id", label: "Premise", type: "select", required: true, optionsEndpoint: "/premises", readOnlyOnEdit: true },
            { name: "installation_date", label: "Installation Date", type: "date" },
          ]}
          columns={[
            { key: "meter_no", label: "Meter No" },
            { key: "device_no", label: "Device No" },
            { key: "read_type", label: "Read Type" },
            { key: "is_assigned", label: "Assigned", render: (m) => <StatusBadge status={m.is_assigned ? "Assigned" : "Available"} tone={m.is_assigned ? "blue" : "green"} /> },
          ]}
        />
      )}

      {tab === "Routes" && (
        <SimpleCrud
          resourceKey="routes" endpoint="/routes" title="Routes" canDelete={false}
          fields={[
            { name: "name", label: "Route Name", type: "text", required: true },
            { name: "read_type", label: "Read Type", type: "select", required: true, options: [{ value: "Manual", label: "Manual" }, { value: "Smart", label: "Smart" }, { value: "Photo", label: "Photo" }, { value: "Estimated", label: "Estimated" }] },
            { name: "premise_id", label: "Premise", type: "select", required: true, optionsEndpoint: "/premises", readOnlyOnEdit: true },
            { name: "utility_service_ids", label: "Utility Service", type: "multiselect", required: true, optionsEndpoint: "/services/catalogue", readOnlyOnEdit: true },
          ]}
          columns={[{ key: "name", label: "Name" }, { key: "read_type", label: "Read Type" }, { key: "meter_count", label: "Meter Count" }]}
        />
      )}

      {tab === "Read Cycles" && (
        <SimpleCrud
          resourceKey="read-cycles" endpoint="/read-cycles" title="Read Cycles" canDelete={false}
          fields={[
            { name: "name", label: "Cycle Name", type: "text", required: true },
            { name: "read_type", label: "Read Type", type: "select", required: true, options: [{ value: "Manual", label: "Manual" }, { value: "Smart", label: "Smart" }, { value: "Photo", label: "Photo" }, { value: "Estimated", label: "Estimated" }] },
            { name: "route_id", label: "Route", type: "select", required: true, optionsEndpoint: "/routes", readOnlyOnEdit: true },
            { name: "utility_service_ids", label: "Utility Service", type: "multiselect", required: true, optionsEndpoint: "/services/catalogue", readOnlyOnEdit: true },
          ]}
          columns={[{ key: "name", label: "Name" }, { key: "read_type", label: "Read Type" }, { key: "meter_count", label: "Meter Count" }]}
        />
      )}

      {tab === "Schedules" && <MeterSchedulesTab />}
      {tab === "Meter Runs" && <MeterRunsTab />}
    </PageShell>
  );
}
