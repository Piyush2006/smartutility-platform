"use client";

import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageShell } from "@/components/PageShell";
import { DataTable } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { api } from "@/lib/api";

interface ConsumptionPoint {
  period_end: string;
  usage: number;
}

export default function PortalConsumptionPage() {
  const consumptionQuery = useQuery({ queryKey: ["portal-consumption"], queryFn: async () => (await api.get<ConsumptionPoint[]>("/portal/consumption")).data });
  const data = consumptionQuery.data ?? [];

  const total = data.reduce((sum, d) => sum + d.usage, 0);
  const average = data.length ? total / data.length : 0;
  const latest = data.length ? data[data.length - 1].usage : null;
  const previous = data.length > 1 ? data[data.length - 2].usage : null;
  const trendPct = previous != null && previous !== 0 && latest != null ? ((latest - previous) / previous) * 100 : null;

  return (
    <PageShell title="My Consumption">
      <div className="space-y-6">
        {consumptionQuery.isError ? (
          <ErrorText error={consumptionQuery.error} />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Latest Reading Usage</p>
                <p className="mt-1 text-2xl font-semibold text-slate-900">{latest != null ? latest.toFixed(1) : "—"}</p>
                {trendPct != null && (
                  <p className={`mt-1 text-xs font-medium ${trendPct >= 0 ? "text-amber-600" : "text-emerald-600"}`}>
                    {trendPct >= 0 ? "▲" : "▼"} {Math.abs(trendPct).toFixed(0)}% vs previous cycle
                  </p>
                )}
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Average per Cycle</p>
                <p className="mt-1 text-2xl font-semibold text-slate-900">{data.length ? average.toFixed(1) : "—"}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Total Usage ({data.length} cycles)</p>
                <p className="mt-1 text-2xl font-semibold text-slate-900">{data.length ? total.toFixed(1) : "—"}</p>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="mb-3 text-sm font-medium text-slate-700">Consumption Trend</h2>
              {data.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-400">No completed readings yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="period_end" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="usage" stroke="#0f172a" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            {data.length > 0 && (
              <div>
                <h2 className="mb-3 text-sm font-medium text-slate-700">Reading History</h2>
                <DataTable<ConsumptionPoint & { id: string }>
                  columns={[
                    { key: "period_end", label: "Period End" },
                    { key: "usage", label: "Usage", render: (r) => r.usage.toFixed(1) },
                  ]}
                  rows={[...data].reverse().map((d) => ({ ...d, id: d.period_end }))}
                />
              </div>
            )}
          </>
        )}
      </div>
    </PageShell>
  );
}
