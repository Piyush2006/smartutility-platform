"use client";

import { useState } from "react";
import { PageShell } from "@/components/PageShell";
import { SimpleCrud, FieldDef } from "@/components/SimpleCrud";
import { Column } from "@/components/DataTable";

interface Level {
  key: string;
  label: string;
  endpoint: string;
  parentField?: string;
  parentEndpoint?: string;
  extraFields?: FieldDef[];
}

const LEVELS: Level[] = [
  { key: "regions", label: "Region", endpoint: "/regions" },
  { key: "countries", label: "Country", endpoint: "/countries", parentField: "region_id", parentEndpoint: "/regions" },
  { key: "states", label: "State", endpoint: "/states", parentField: "country_id", parentEndpoint: "/countries" },
  { key: "cities", label: "City", endpoint: "/cities", parentField: "state_id", parentEndpoint: "/states" },
  { key: "zones", label: "Zone", endpoint: "/zones", parentField: "city_id", parentEndpoint: "/cities" },
  { key: "divisions", label: "Division", endpoint: "/divisions", parentField: "zone_id", parentEndpoint: "/zones" },
  { key: "areas", label: "Area", endpoint: "/areas", parentField: "division_id", parentEndpoint: "/divisions" },
  {
    key: "sub-areas", label: "Sub-Area", endpoint: "/sub-areas", parentField: "area_id", parentEndpoint: "/areas",
    extraFields: [{ name: "servicable", label: "Servicable", type: "checkbox" }],
  },
  {
    key: "premises", label: "Premise", endpoint: "/premises", parentField: "sub_area_id", parentEndpoint: "/sub-areas",
    extraFields: [
      { name: "latitude", label: "Latitude", type: "number" },
      { name: "longitude", label: "Longitude", type: "number" },
    ],
  },
];

export default function TerritoryPage() {
  const [active, setActive] = useState(LEVELS[0].key);
  const level = LEVELS.find((l) => l.key === active)!;

  const fields: FieldDef[] = [
    ...(level.parentField ? [{ name: level.parentField, label: `Parent ${LEVELS.find((l) => l.endpoint === level.parentEndpoint)?.label}`, type: "select" as const, required: true, optionsEndpoint: level.parentEndpoint }] : []),
    { name: "name", label: "Name", type: "text", required: true },
    ...(level.extraFields ?? []),
  ];

  const columns: Column<{ id: string; name: string }>[] = [
    { key: "name", label: "Name" },
    ...(level.parentField ? [{ key: level.parentField, label: "Parent" }] : []),
  ];

  return (
    <PageShell title="Territory">
      <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200">
        {LEVELS.map((l) => (
          <button
            key={l.key}
            onClick={() => setActive(l.key)}
            className={`rounded-t-md px-3 py-2 text-sm font-medium ${active === l.key ? "border-b-2 border-slate-900 text-slate-900" : "text-slate-500 hover:text-slate-800"}`}
          >
            {l.label}
          </button>
        ))}
      </div>
      <SimpleCrud key={level.key} resourceKey={level.key} endpoint={level.endpoint} title={level.label} fields={fields} columns={columns} />
    </PageShell>
  );
}
