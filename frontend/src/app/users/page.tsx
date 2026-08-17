"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { PageShell } from "@/components/PageShell";
import { DataTable, StatusBadge } from "@/components/DataTable";
import { ErrorText } from "@/components/ErrorText";
import { Modal } from "@/components/Modal";
import { api } from "@/lib/api";
import type { PermissionSummaryOut, RoleDetailOut, RoleSummaryOut, TenantUserOut, UserInviteOut } from "@/lib/types";

const TABS = ["Users", "Roles"] as const;

interface InviteForm {
  full_name: string;
  email: string;
  role_id: string;
}

interface EditForm {
  full_name: string;
  is_active: boolean;
  role_id: string;
}

function UserDetailModal({ user, roles, onClose }: { user: TenantUserOut; roles?: RoleSummaryOut[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const { register, handleSubmit, reset } = useForm<EditForm>();

  useEffect(() => {
    reset({ full_name: user.full_name, is_active: user.is_active, role_id: user.roles[0]?.id ?? "" });
  }, [user, reset]);

  const updateMutation = useMutation({
    mutationFn: async (values: EditForm) => (await api.patch(`/users/${user.id}`, values)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
      onClose();
    },
  });

  return (
    <Modal title={editing ? `Edit ${user.full_name}` : user.full_name} onClose={onClose}>
      {editing ? (
        <form onSubmit={handleSubmit((v) => updateMutation.mutate(v))} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Full Name</label>
            <input {...register("full_name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Role</label>
            <select {...register("role_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
              {roles?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" {...register("is_active")} className="h-4 w-4" /> Active
          </label>
          <p className="text-xs text-slate-400">Email can&apos;t be changed after the account is created.</p>
          <ErrorText error={updateMutation.error} />
          <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Save</button>
        </form>
      ) : (
        <div className="space-y-2 text-sm">
          <p><span className="text-slate-400">Email:</span> {user.email}</p>
          <p><span className="text-slate-400">Role:</span> {user.roles.map((r) => r.name).join(", ") || "—"}</p>
          <p><span className="text-slate-400">Status:</span> <StatusBadge status={user.is_active ? "Active" : "Inactive"} tone={user.is_active ? "green" : "slate"} /></p>
          <button onClick={() => setEditing(true)} className="mt-2 w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Edit</button>
        </div>
      )}
    </Modal>
  );
}

function InviteResultModal({ result, onClose }: { result: UserInviteOut; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <Modal title="User Invited" onClose={onClose}>
      {result.email_sent ? (
        <p className="text-sm text-slate-600">
          An invite email was sent to <strong>{result.user.email}</strong> with a link to set their password.
        </p>
      ) : (
        <div className="space-y-3 text-sm">
          <p className="text-slate-600">
            No email server is configured yet, so <strong>{result.user.email}</strong> wasn&apos;t actually emailed. Share this
            one-time invite link with them yourself -- it lets them set their own password:
          </p>
          <div className="flex items-center gap-2 rounded-md bg-slate-50 p-3">
            <code className="flex-1 break-all text-xs text-slate-700">{result.invite_link}</code>
            <button
              onClick={() => {
                navigator.clipboard.writeText(result.invite_link);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              className="shrink-0 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <p className="text-xs text-slate-400">Expires in 7 days. Set SMTP_HOST/SMTP_FROM_EMAIL etc. in the backend .env to send these for real.</p>
        </div>
      )}
    </Modal>
  );
}

function UsersTab() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [viewing, setViewing] = useState<TenantUserOut | null>(null);
  const [inviteResult, setInviteResult] = useState<UserInviteOut | null>(null);
  const { register, handleSubmit, reset, formState } = useForm<InviteForm>();

  const usersQuery = useQuery({ queryKey: ["tenant-users"], queryFn: async () => (await api.get<TenantUserOut[]>("/users")).data });
  const rolesQuery = useQuery({ queryKey: ["tenant-roles"], queryFn: async () => (await api.get<RoleSummaryOut[]>("/roles")).data });
  const invitableRoles = rolesQuery.data?.filter((r) => r.name !== "Consumer");

  const inviteMutation = useMutation({
    mutationFn: async (values: InviteForm) => (await api.post<UserInviteOut>("/users", values)).data,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["tenant-users"] });
      setInviteResult(data);
      setOpen(false);
      reset();
    },
  });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-700">Staff Users</h2>
        <button onClick={() => setOpen(true)} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          + Invite User
        </button>
      </div>

      {usersQuery.isError ? (
        <ErrorText error={usersQuery.error} />
      ) : (
        <DataTable<TenantUserOut>
          columns={[
            { key: "full_name", label: "Name" },
            { key: "email", label: "Email" },
            { key: "roles", label: "Role", render: (u) => u.roles.map((r) => r.name).join(", ") || "—" },
            { key: "is_active", label: "Status", render: (u) => <StatusBadge status={u.is_active ? "Active" : "Inactive"} tone={u.is_active ? "green" : "slate"} /> },
            { key: "id", label: "Action", render: (u) => <button onClick={() => setViewing(u)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View</button> },
          ]}
          rows={usersQuery.data ?? []}
          emptyLabel="No staff users yet -- invite one above."
        />
      )}

      {viewing && <UserDetailModal user={viewing} roles={invitableRoles} onClose={() => setViewing(null)} />}

      {open && (
        <Modal title="Invite User" onClose={() => setOpen(false)}>
          <form onSubmit={handleSubmit((v) => inviteMutation.mutate(v))} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Full Name</label>
              <input {...register("full_name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Email</label>
              <input type="email" {...register("email", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Role</label>
              <select {...register("role_id", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm">
                <option value="">Select…</option>
                {invitableRoles?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
            <p className="text-xs text-slate-400">They&apos;ll get a link to set their own password -- no password is generated here.</p>
            <ErrorText error={inviteMutation.error} />
            <button type="submit" disabled={formState.isSubmitting} className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              Send Invite
            </button>
          </form>
        </Modal>
      )}

      {inviteResult && <InviteResultModal result={inviteResult} onClose={() => setInviteResult(null)} />}
    </div>
  );
}

const MODULE_ORDER = ["tenant", "territory", "account", "consumer", "meter", "reading", "vee", "billing", "reports", "integration", "audit", "users", "portal"];

function groupPermissionsByModule(permissions: PermissionSummaryOut[]) {
  const groups = new Map<string, PermissionSummaryOut[]>();
  for (const p of permissions) {
    if (!groups.has(p.module)) groups.set(p.module, []);
    groups.get(p.module)!.push(p);
  }
  return [...groups.entries()].sort((a, b) => MODULE_ORDER.indexOf(a[0]) - MODULE_ORDER.indexOf(b[0]));
}

interface RoleForm {
  name: string;
  description: string;
  permission_ids: string[];
}

function RoleFormModal({ role, onClose }: { role: RoleDetailOut | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const isEdit = !!role;
  const permissionsQuery = useQuery({ queryKey: ["permission-catalogue"], queryFn: async () => (await api.get<PermissionSummaryOut[]>("/permissions")).data });
  const { register, handleSubmit, watch, setValue } = useForm<RoleForm>({ defaultValues: { permission_ids: [] } });
  const selected = new Set(watch("permission_ids"));

  useEffect(() => {
    if (role) setValue("permission_ids", role.permissions.map((p) => p.id));
  }, [role, setValue]);

  const saveMutation = useMutation({
    mutationFn: async (values: RoleForm) => {
      const payload = { name: values.name, description: values.description || undefined, permission_ids: values.permission_ids };
      return isEdit ? (await api.patch(`/roles/${role!.id}`, payload)).data : (await api.post("/roles", payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-roles"] });
      onClose();
    },
  });

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setValue("permission_ids", [...next]);
  }

  return (
    <Modal title={isEdit ? `Edit ${role!.name}` : "New Role"} onClose={onClose}>
      <form onSubmit={handleSubmit((v) => saveMutation.mutate(v))} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-slate-700">Role Name</label>
          <input defaultValue={role?.name} {...register("name", { required: true })} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Description</label>
          <input defaultValue={role?.description ?? ""} {...register("description")} className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">Permissions</label>
          {permissionsQuery.isLoading ? (
            <p className="mt-1 text-sm text-slate-400">Loading…</p>
          ) : (
            <div className="mt-1 max-h-72 space-y-3 overflow-y-auto rounded-md border border-slate-200 p-3">
              {groupPermissionsByModule(permissionsQuery.data ?? []).map(([module, perms]) => (
                <div key={module}>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{module}</p>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
                    {perms.map((p) => (
                      <label key={p.id} className="flex items-center gap-1.5 text-sm text-slate-700">
                        <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} className="h-3.5 w-3.5" />
                        {p.action}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <ErrorText error={saveMutation.error} />
        <button type="submit" className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
          {isEdit ? "Save" : "Create Role"}
        </button>
      </form>
    </Modal>
  );
}

function RoleDetailModal({ role, onClose, onEdit, onDeleted }: { role: RoleSummaryOut; onClose: () => void; onEdit: (detail: RoleDetailOut) => void; onDeleted: () => void }) {
  const queryClient = useQueryClient();
  const detailQuery = useQuery({ queryKey: ["role-detail", role.id], queryFn: async () => (await api.get<RoleDetailOut>(`/roles/${role.id}`)).data });

  const deleteMutation = useMutation({
    mutationFn: async () => api.delete(`/roles/${role.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-roles"] });
      onDeleted();
    },
  });

  return (
    <Modal title={role.name} onClose={onClose}>
      {detailQuery.isLoading && <p className="text-sm text-slate-400">Loading…</p>}
      {detailQuery.isError && <ErrorText error={detailQuery.error} />}
      {detailQuery.data && (
        <div className="space-y-3 text-sm">
          {role.description && <p className="text-slate-600">{role.description}</p>}
          <p><span className="text-slate-400">Type:</span> {role.is_system ? "System role (from workbook)" : "Custom role"}</p>
          <div>
            <p className="mb-1 font-medium text-slate-700">Permissions ({detailQuery.data.permissions.length})</p>
            {detailQuery.data.permissions.length === 0 ? (
              <p className="text-xs text-slate-400">No permissions granted to this role.</p>
            ) : (
              <div className="max-h-72 overflow-y-auto rounded-md border border-slate-200">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-slate-500">
                    <tr>
                      <th className="px-3 py-1.5 text-left font-medium">Module</th>
                      <th className="px-3 py-1.5 text-left font-medium">Resource</th>
                      <th className="px-3 py-1.5 text-left font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detailQuery.data.permissions.map((p) => (
                      <tr key={p.id} className="border-t border-slate-100">
                        <td className="px-3 py-1">{p.module}</td>
                        <td className="px-3 py-1">{p.resource}</td>
                        <td className="px-3 py-1">{p.action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          {!role.is_system && (
            <>
              <ErrorText error={deleteMutation.error} />
              <div className="flex gap-2">
                <button onClick={() => onEdit(detailQuery.data!)} className="flex-1 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">Edit</button>
                <button
                  onClick={() => { if (window.confirm(`Delete role "${role.name}"?`)) deleteMutation.mutate(); }}
                  className="flex-1 rounded-md border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </Modal>
  );
}

function RolesTab() {
  const [viewing, setViewing] = useState<RoleSummaryOut | null>(null);
  const [formRole, setFormRole] = useState<RoleDetailOut | null>(null);
  const [creating, setCreating] = useState(false);
  const rolesQuery = useQuery({ queryKey: ["tenant-roles"], queryFn: async () => (await api.get<RoleSummaryOut[]>("/roles")).data });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-500">
          System roles come from the workbook and can&apos;t be edited. Build a custom role below to grant exactly the
          permissions you need.
        </p>
        <button onClick={() => setCreating(true)} className="shrink-0 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          + Create Role
        </button>
      </div>
      {rolesQuery.isError ? (
        <ErrorText error={rolesQuery.error} />
      ) : (
        <DataTable<RoleSummaryOut>
          columns={[
            { key: "name", label: "Role" },
            { key: "description", label: "Description" },
            { key: "is_system", label: "Type", render: (r) => <StatusBadge status={r.is_system ? "System" : "Custom"} tone={r.is_system ? "slate" : "blue"} /> },
            { key: "id", label: "Action", render: (r) => <button onClick={() => setViewing(r)} className="text-xs font-medium text-slate-600 underline hover:text-slate-900">View Permissions</button> },
          ]}
          rows={rolesQuery.data ?? []}
        />
      )}
      {viewing && (
        <RoleDetailModal
          role={viewing} onClose={() => setViewing(null)}
          onEdit={(detail) => { setViewing(null); setFormRole(detail); }}
          onDeleted={() => setViewing(null)}
        />
      )}
      {(creating || formRole) && <RoleFormModal role={formRole} onClose={() => { setCreating(false); setFormRole(null); }} />}
    </div>
  );
}

export default function UsersPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Users");

  return (
    <PageShell title="Users & Roles">
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
      {tab === "Users" && <UsersTab />}
      {tab === "Roles" && <RolesTab />}
    </PageShell>
  );
}
