"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listAliases,
  listProviders,
  createAlias,
  updateAlias,
  deleteAlias,
  type Alias,
  type AliasIn,
} from "@/lib/api";
import { PageShell } from "@/components/page-shell";

function AliasForm({
  initial,
  providers,
  onSave,
  onCancel,
}: {
  initial?: Alias;
  providers: string[];
  onSave: (v: AliasIn) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState<AliasIn>(
    initial
      ? {
          alias_name: initial.alias_name,
          provider_id: initial.provider_id,
          native_id: initial.native_id,
          priority: initial.priority,
          is_active: initial.is_active,
        }
      : {
          alias_name: "",
          provider_id: providers[0] ?? "",
          native_id: "",
          priority: 100,
          is_active: true,
        }
  );

  return (
    <div className="bg-card border rounded-lg p-6 space-y-4 mb-6">
      <h2 className="font-semibold">{initial ? "Edit Alias" : "New Alias"}</h2>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="field-label">Alias Name</label>
          <input className="input" value={v.alias_name} disabled={!!initial} onChange={(e) => setV({ ...v, alias_name: e.target.value })} />
        </div>
        <div>
          <label className="field-label">Provider</label>
          <select className="input" value={v.provider_id} onChange={(e) => setV({ ...v, provider_id: e.target.value })}>
            {providers.map((p) => <option key={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label className="field-label">Native ID</label>
          <input className="input" value={v.native_id} onChange={(e) => setV({ ...v, native_id: e.target.value })} />
        </div>
        <div>
          <label className="field-label">Priority (lower = higher priority)</label>
          <input className="input" type="number" value={v.priority} onChange={(e) => setV({ ...v, priority: Number(e.target.value) })} />
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={v.is_active} onChange={(e) => setV({ ...v, is_active: e.target.checked })} />
            Active
          </label>
        </div>
      </div>
      <div className="flex gap-2">
        <button className="btn-primary" onClick={() => onSave(v)}>Save</button>
        <button className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function AliasesPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Alias | null | "new">(null);

  const { data: aliases = [], isLoading } = useQuery({ queryKey: ["aliases"], queryFn: listAliases });
  const { data: providers = [] } = useQuery({ queryKey: ["providers"], queryFn: listProviders });
  const providerIds = providers.map((p) => p.id);

  const create = useMutation({
    mutationFn: createAlias,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["aliases"] }); setEditing(null); },
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { priority?: number; is_active?: boolean } }) => updateAlias(id, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["aliases"] }); setEditing(null); },
  });
  const del = useMutation({
    mutationFn: deleteAlias,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["aliases"] }),
  });

  function handleSave(v: AliasIn) {
    if (editing === "new") {
      create.mutate(v);
    } else if (editing) {
      update.mutate({ id: editing.id, body: { priority: v.priority, is_active: v.is_active } });
    }
  }

  // group by alias_name for display
  const grouped = aliases.reduce<Record<string, Alias[]>>((acc, a) => {
    (acc[a.alias_name] ??= []).push(a);
    return acc;
  }, {});

  return (
    <PageShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">Aliases</h1>
        <button className="btn-primary" onClick={() => setEditing("new")}>+ New Alias</button>
      </div>

      {editing && (
        <AliasForm
          initial={editing === "new" ? undefined : editing}
          providers={providerIds}
          onSave={handleSave}
          onCancel={() => setEditing(null)}
        />
      )}

      {isLoading && <p className="text-muted-foreground">Loading…</p>}

      <div className="space-y-4">
        {Object.entries(grouped).map(([name, entries]) => (
          <div key={name} className="bg-card border rounded-lg overflow-hidden">
            <div className="px-4 py-2 border-b bg-muted/30 font-mono text-sm font-medium">{name}</div>
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/10">
                <tr>
                  {["Priority", "Provider", "Native ID", "Status", ""].map((h) => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.sort((a, b) => a.priority - b.priority).map((a) => (
                  <tr key={a.id} className="border-b last:border-0 hover:bg-muted/20">
                    <td className="px-4 py-2">{a.priority}</td>
                    <td className="px-4 py-2 text-xs">{a.provider_id}</td>
                    <td className="px-4 py-2 font-mono text-xs">{a.native_id}</td>
                    <td className="px-4 py-2">
                      <span className={`badge ${a.is_active ? "badge-green" : "badge-gray"}`}>
                        {a.is_active ? "active" : "inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-2 flex gap-2 justify-end">
                      <button className="btn-ghost text-xs" onClick={() => setEditing(a)}>Edit</button>
                      <button className="btn-ghost text-xs text-destructive" onClick={() => { if (confirm(`Delete alias #${a.id}?`)) del.mutate(a.id); }}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
