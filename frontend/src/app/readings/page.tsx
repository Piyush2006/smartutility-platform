"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { api } from "@/lib/api";
import type { MeterOut, MeterReadingOut, ValidationBreakdownOut } from "@/lib/types";

interface ManualForm {
  meter_id: string;
  current_reading: number;
  current_reading_date: string;
}

interface UploadForm {
  file: FileList;
}

function statusTone(status: string): "slate" | "green" | "amber" | "red" | "blue" {
  if (status === "Completed") return "green";
  if (status === "Revisit") return "red";
  if (status === "V1" || status === "V2") return "amber";
  return "blue";
}

export default function ReadingsPage() {
  const queryClient = useQueryClient();
  const metersQuery = useQuery({ queryKey: ["meters"], queryFn: async () => (await api.get<MeterOut[]>("/meters")).data });
  const readingsQuery = useQuery({ queryKey: ["meter-readings"], queryFn: async () => (await api.get<MeterReadingOut[]>("/meter-readings")).data });
  const breakdownQuery = useQuery({ queryKey: ["validation-breakdown"], queryFn: async () => (await api.get<ValidationBreakdownOut[]>("/meter-readings/validation-breakdown")).data });

  const { register: registerManual, handleSubmit: handleManual, reset: resetManual } = useForm<ManualForm>();
  const manualMutation = useMutation({
    mutationFn: async (values: ManualForm) => (await api.post("/meter-readings", { ...values, current_reading: Number(values.current_reading) })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meter-readings"] });
      queryClient.invalidateQueries({ queryKey: ["validation-breakdown"] });
      resetManual();
    },
  });

  const { register: registerUpload, handleSubmit: handleUpload, reset: resetUpload } = useForm<UploadForm>();
  const uploadMutation = useMutation({
    mutationFn: async (values: UploadForm) => {
      const form = new FormData();
      form.append("file", values.file[0]);
      return (await api.post("/meter-readings/upload", form, { headers: { "Content-Type": "multipart/form-data" } })).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meter-readings"] });
      queryClient.invalidateQueries({ queryKey: ["validation-breakdown"] });
      resetUpload();
    },
  });

  const resolveMutation = useMutation({
    mutationFn: async (id: string) => (await api.post(`/meter-readings/${id}/resolve-revisit`, {})).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meter-readings"] });
      queryClient.invalidateQueries({ queryKey: ["validation-breakdown"] });
    },
  });

  return (
    <PageShell title="Meter Readings">
      <div className="space-y-8">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-medium text-slate-700">Manual Entry</h2>
            <form onSubmit={handleManual((v) => manualMutation.mutate(v))} className="space-y-2">
              <select {...registerManual("meter_id", { required: true })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                <option value="">Select meter…</option>
                {metersQuery.data?.map((m) => <option key={m.id} value={m.id}>{m.meter_no} ({m.device_no})</option>)}
              </select>
              <input type="number" step="any" placeholder="Current reading" {...registerManual("current_reading", { required: true })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              <input type="date" {...registerManual("current_reading_date", { required: true })} className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              <ErrorText error={manualMutation.error} />
              <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Submit Reading</button>
            </form>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-medium text-slate-700">CSV / XLSX Upload</h2>
            <p className="mb-2 text-xs text-slate-400">
              Columns: device_no, current_reading, current_reading_date. <a href={`${process.env.NEXT_PUBLIC_API_URL}/meter-readings/template`} className="underline">Download template</a>
            </p>
            <form onSubmit={handleUpload((v) => uploadMutation.mutate(v))} className="space-y-2">
              <input type="file" accept=".csv,.xlsx" {...registerUpload("file", { required: true })} className="w-full text-sm" />
              <ErrorText error={uploadMutation.error} />
              <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Upload</button>
            </form>
            {uploadMutation.data && (
              <p className="mt-2 text-xs text-slate-500">
                {uploadMutation.data.valid_rows} valid / {uploadMutation.data.invalid_rows} invalid of {uploadMutation.data.total_rows} rows.
              </p>
            )}
          </div>
        </div>

        {(metersQuery.isError || readingsQuery.isError || breakdownQuery.isError || resolveMutation.isError) && (
          <ErrorText error={metersQuery.error ?? readingsQuery.error ?? breakdownQuery.error ?? resolveMutation.error} />
        )}

        <div>
          <h2 className="mb-3 text-sm font-medium text-slate-700">Validation Dashboard (VEE)</h2>
          <DataTable
            columns={[
              { key: "read_cycle_name", label: "Read Cycle" },
              { key: "total_meters", label: "Total Meters" },
              { key: "readings", label: "Readings" },
              { key: "pending", label: "Pending" },
              { key: "v1", label: "V1" },
              { key: "v2", label: "V2" },
              { key: "revisit", label: "Revisit" },
              { key: "completed", label: "Completed" },
            ]}
            rows={(breakdownQuery.data ?? []).map((r) => ({ ...r, id: r.read_cycle_id }))}
          />
        </div>

        <div>
          <h2 className="mb-3 text-sm font-medium text-slate-700">Recent Readings</h2>
          <DataTable<MeterReadingOut>
            columns={[
              { key: "meter_id", label: "Meter", render: (r) => { const m = metersQuery.data?.find((x) => x.id === r.meter_id); return m ? `${m.meter_no} (${m.device_no})` : r.meter_id; } },
              { key: "previous_reading", label: "Prev Reading" },
              { key: "previous_reading_date", label: "Prev Date" },
              { key: "current_reading", label: "Current Reading" },
              { key: "current_reading_date", label: "Current Date" },
              { key: "status", label: "Status", render: (r) => <StatusBadge status={r.status} tone={statusTone(r.status)} /> },
              {
                key: "id", label: "Action",
                render: (r) => r.status === "Revisit" ? (
                  <button onClick={() => resolveMutation.mutate(r.id)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">Resolve</button>
                ) : null,
              },
            ]}
            rows={readingsQuery.data ?? []}
          />
        </div>
      </div>
    </PageShell>
  );
}
