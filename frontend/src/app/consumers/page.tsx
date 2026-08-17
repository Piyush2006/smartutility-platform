"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { Modal } from "@/components/Modal";
import { api } from "@/lib/api";
import type { ConsumerOut, MeterOut, PlanOut, PremiseOut } from "@/lib/types";

interface ConsumerForm {
  full_name: string;
  contact_no: string;
  email_address: string;
  ssn: string;
  premise_id: string;
  service_address: string;
  billing_address: string;
  plan_id: string;
  activation_date: string;
  meter_id: string;
  first_meter_reading: number;
  first_meter_reading_date: string;
  id_file: FileList;
}

interface ConsumerEditForm {
  full_name: string;
  contact_no: string;
  email_address: string;
  service_address: string;
  billing_address: string;
  plan_id: string;
  status: string;
}

function ConsumerDetailModal({ consumer, plans, onClose }: { consumer: ConsumerOut; plans?: PlanOut[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const { register, handleSubmit, reset } = useForm<ConsumerEditForm>();

  useEffect(() => {
    reset({
      full_name: consumer.full_name, contact_no: consumer.contact_no, email_address: consumer.email_address,
      service_address: consumer.service_address, billing_address: consumer.billing_address, plan_id: consumer.plan_id, status: consumer.status,
    });
  }, [consumer, reset]);

  const updateMutation = useMutation({
    mutationFn: async (values: ConsumerEditForm) => (await api.patch(`/consumers/${consumer.id}`, values)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consumers"] });
      onClose();
    },
  });

  return (
    <Modal title={editing ? `Edit ${consumer.full_name}` : consumer.full_name} onClose={onClose}>
      {editing ? (
        <form onSubmit={handleSubmit((v) => updateMutation.mutate(v))} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Full Name</label>
            <input {...register("full_name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Contact No</label>
              <input {...register("contact_no", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Email</label>
              <input type="email" {...register("email_address", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Service Address</label>
              <input {...register("service_address", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Billing Address</label>
              <input {...register("billing_address", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Plan</label>
              <select {...register("plan_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                {plans?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Status</label>
              <select {...register("status", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
          <p className="text-xs text-slate-400">Premise, meter, SSN and ID document can&apos;t be changed here.</p>
          <ErrorText error={updateMutation.error} />
          <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Save</button>
        </form>
      ) : (
        <div className="space-y-2 text-sm">
          <p><span className="text-slate-400">Contact:</span> {consumer.contact_no}</p>
          <p><span className="text-slate-400">Email:</span> {consumer.email_address}</p>
          <p><span className="text-slate-400">Service Address:</span> {consumer.service_address}</p>
          <p><span className="text-slate-400">Billing Address:</span> {consumer.billing_address}</p>
          <p><span className="text-slate-400">Plan:</span> {plans?.find((p) => p.id === consumer.plan_id)?.name ?? consumer.plan_id}</p>
          <p><span className="text-slate-400">Activation Date:</span> {consumer.activation_date}</p>
          <p><span className="text-slate-400">First Meter Reading:</span> {consumer.first_meter_reading} ({consumer.first_meter_reading_date})</p>
          <p><span className="text-slate-400">Status:</span> <StatusBadge status={consumer.status} tone={consumer.status === "active" ? "green" : "slate"} /></p>
          <button onClick={() => setEditing(true)} className="mt-2 w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Edit</button>
        </div>
      )}
    </Modal>
  );
}

export default function ConsumersPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [viewing, setViewing] = useState<ConsumerOut | null>(null);
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null);
  const { register, handleSubmit, reset, formState } = useForm<ConsumerForm>();

  const consumersQuery = useQuery({ queryKey: ["consumers"], queryFn: async () => (await api.get<ConsumerOut[]>("/consumers")).data });
  const premisesQuery = useQuery({ queryKey: ["/premises"], queryFn: async () => (await api.get<PremiseOut[]>("/premises")).data, enabled: open });
  const plansQuery = useQuery({ queryKey: ["plans"], queryFn: async () => (await api.get<PlanOut[]>("/plans")).data, enabled: open || !!viewing });
  const metersQuery = useQuery({ queryKey: ["meters-available"], queryFn: async () => (await api.get<MeterOut[]>("/meters/available")).data, enabled: open });

  const createMutation = useMutation({
    mutationFn: async (values: ConsumerForm) => {
      const form = new FormData();
      form.append("file", values.id_file[0]);
      const idDoc = await api.post("/consumers/id-document", form, { headers: { "Content-Type": "multipart/form-data" } });
      const payload = { ...values, id_document_url: idDoc.data.url, first_meter_reading: Number(values.first_meter_reading) };
      delete (payload as Partial<ConsumerForm>).id_file;
      return (await api.post("/consumers", payload)).data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["consumers"] });
      setCredentials({ email: data.portal_email, password: data.portal_temp_password });
      setOpen(false);
      reset();
    },
  });

  return (
    <PageShell title="Consumers">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-700">Consumers</h2>
        <button onClick={() => setOpen(true)} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          + Add Consumer
        </button>
      </div>

      {consumersQuery.isError ? (
        <ErrorText error={consumersQuery.error} />
      ) : (
        <DataTable<ConsumerOut>
          columns={[
            { key: "full_name", label: "Name" },
            { key: "contact_no", label: "Contact" },
            { key: "email_address", label: "Email" },
            { key: "status", label: "Status", render: (c) => <StatusBadge status={c.status} tone={c.status === "active" ? "green" : "slate"} /> },
            { key: "id", label: "Action", render: (c) => <button onClick={() => setViewing(c)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View</button> },
          ]}
          rows={consumersQuery.data ?? []}
        />
      )}

      {viewing && <ConsumerDetailModal consumer={viewing} plans={plansQuery.data} onClose={() => setViewing(null)} />}

      {open && (
        <Modal title="New Consumer" onClose={() => setOpen(false)}>
          <form onSubmit={handleSubmit((v) => createMutation.mutate(v))} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Full Name</label>
              <input {...register("full_name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Contact No (+E.164)</label>
                <input {...register("contact_no", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Email</label>
                <input type="email" {...register("email_address", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">SSN (XXX-XX-XXXX)</label>
                <input {...register("ssn", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">ID Document (pdf/jpg/png)</label>
                <input type="file" accept=".pdf,.jpg,.jpeg,.png" {...register("id_file", { required: true })} className="mt-1 w-full text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Premise</label>
              <select {...register("premise_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                <option value="">Select…</option>
                {premisesQuery.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Service Address</label>
                <input {...register("service_address", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Billing Address</label>
                <input {...register("billing_address", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Plan</label>
                <select {...register("plan_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                  <option value="">Select…</option>
                  {plansQuery.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Activation Date</label>
                <input type="date" {...register("activation_date", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Meter</label>
              <select {...register("meter_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                <option value="">Select available meter…</option>
                {metersQuery.data?.map((m) => <option key={m.id} value={m.id}>{m.meter_no} ({m.device_no})</option>)}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">First Meter Reading</label>
                <input type="number" step="any" {...register("first_meter_reading", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">First Reading Date</label>
                <input type="date" {...register("first_meter_reading_date", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
              </div>
            </div>
            <ErrorText error={createMutation.error} />
            <button type="submit" disabled={formState.isSubmitting} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              Save Consumer
            </button>
          </form>
        </Modal>
      )}

      {credentials && (
        <Modal title="Consumer Portal Credentials" onClose={() => setCredentials(null)}>
          <p className="text-sm text-slate-600">Share these with the consumer for portal access:</p>
          <div className="mt-3 rounded-md bg-slate-50 p-3 text-sm">
            <p><span className="text-slate-400">Email:</span> {credentials.email}</p>
            <p><span className="text-slate-400">Temp password:</span> {credentials.password}</p>
          </div>
        </Modal>
      )}
    </PageShell>
  );
}
