"use client";

import { PageShell } from "@/components/PageShell";
import { SimpleCrud } from "@/components/SimpleCrud";
import type { VeeConfigOut, VeeScheduleOut } from "@/lib/types";

const READ_TYPE_OPTIONS = [
  { value: "Manual", label: "Manual" },
  { value: "Smart", label: "Smart" },
  { value: "Photo", label: "Photo" },
];

export default function VeePage() {
  return (
    <PageShell title="VEE (Validation, Estimation & Editing)">
      <div className="space-y-10">
        <SimpleCrud
          resourceKey="vee-rules" endpoint="/vee/rules" title="VEE Rules"
          fields={[
            { name: "name", label: "Rule Name", type: "text", required: true },
            { name: "utility_service_id", label: "Utility Service", type: "select", required: true, optionsEndpoint: "/services/catalogue", readOnlyOnEdit: true },
            { name: "read_type", label: "Read Type", type: "select", required: true, options: READ_TYPE_OPTIONS, readOnlyOnEdit: true },
            { name: "rule_type", label: "Rule", type: "select", required: true, options: [{ value: "No Reading", label: "No Reading" }, { value: "Threshold Alert", label: "Threshold Alert" }], readOnlyOnEdit: true },
          ]}
          columns={[{ key: "name", label: "Name" }, { key: "rule_type", label: "Rule" }, { key: "read_type", label: "Read Type" }]}
        />

        <SimpleCrud<VeeConfigOut>
          resourceKey="vee-configs" endpoint="/vee/configs" title="VEE Config" canDelete={false}
          fields={[
            { name: "name", label: "Config Name", type: "text", required: true },
            { name: "utility_service_id", label: "Utility Service", type: "select", required: true, optionsEndpoint: "/services/catalogue", readOnlyOnEdit: true },
            { name: "read_type", label: "Read Type", type: "select", required: true, options: READ_TYPE_OPTIONS, readOnlyOnEdit: true },
            { name: "rule_ids", label: "Rule", type: "multiselect", required: true, optionsEndpoint: "/vee/rules", readOnlyOnEdit: true },
          ]}
          columns={[{ key: "name", label: "Name" }, { key: "read_type", label: "Read Type" }, { key: "rule_ids", label: "Rules", render: (c) => `${c.rule_ids.length} rule(s)` }]}
        />

        <SimpleCrud<VeeScheduleOut>
          resourceKey="vee-schedules" endpoint="/vee/schedules" title="VEE Schedule"
          fields={[
            { name: "vee_config_id", label: "Config", type: "select", required: true, optionsEndpoint: "/vee/configs", readOnlyOnEdit: true },
            { name: "start_date", label: "Schedule Start Date", type: "date", required: true, readOnlyOnEdit: true },
            { name: "repetition_interval", label: "Repetition Interval", type: "select", required: true, options: ["15 min", "30 min", "1 hour", "6 hours", "12 hours", "24 hours"].map((v) => ({ value: v, label: v })), readOnlyOnEdit: true },
            { name: "end_date", label: "Schedule End Date", type: "date", required: true, readOnlyOnEdit: true },
            { name: "is_active", label: "Active", type: "checkbox" },
          ]}
          columns={[{ key: "vee_config_id", label: "Config" }, { key: "start_date", label: "Start" }, { key: "end_date", label: "End" }]}
        />
      </div>
    </PageShell>
  );
}
