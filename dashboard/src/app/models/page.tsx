"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listModels,
  listProviders,
  createModel,
  updateModel,
  deleteModel,
  type Model,
  type ModelIn,
} from "@/lib/api";
import { PageShell } from "@/components/page-shell";

function ModelForm({
  initial,
  providers,
  onSave,
  onCancel,
}: {
  initial?: Model;
  providers: string[];
  onSave: (v: ModelIn) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState<ModelIn>(
    initial
      ? { ...initial, display_name: initial.display_name ?? undefined }
      : {
          id: "",
          provider_id: providers[0] ?? "",
          native_id: "",
          display_name: "",
          context_len: 8192,
          supports_streaming: true,
          supports_vision: false,
          weight: 100,
          is_active: true,
        }
  );

  return (
    <div className="bg-card border rounded-lg p-6 space-y-4 mb-6">
      <h2 className="font-semibold">{initial ? "Edit Model" : "New Model"}</h2>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="field-label">ID (slug)</label>
          <input className="input" value={v.id} disabled={!!initial} onChange={(e) => setV({ ...v, id: e.target.value })} />
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
          <label className="field-label">Display Name</label>
          <input className="input" value={v.display_name ?? ""} onChange={(e) => setV({ ...v, display_name: e.target.value })} />
        </div>
        <div>
          <label className="field-label">Context Length</label>
          <input className="input" type="number" value={v.context_len} onChange={(e) => setV({ ...v, context_len: Number(e.target.value) })} />
        </div>
        <div>
          <label className="field-label">Weight</label>
          <input className="input" type="number" value={v.weight} onChange={(e) => setV({ ...v, weight: Number(e.target.value) })} />
        </div>
        <div className="flex gap-4 col-span-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={v.supports_streaming} onChange={(e) => setV({ ...v, supports_streaming: e.target.checked })} />
            Streaming
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={v.supports_vision} onChange={(e) => setV({ ...v, supports_vision: e.target.checked })} />
            Vision
          </label>
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

export default function ModelsPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Model | null | "new">(null);

  const { data: models = [], isLoading } = useQuery({ queryKey: ["models"], queryFn: listModels });
  const { data: providers = [] } = useQuery({ queryKey: ["providers"], queryFn: listProviders });
  const providerIds = providers.map((p) => p.id);

  const create = useMutation({
    mutationFn: createModel,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["models"] }); setEditing(null); },
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<ModelIn> }) => updateModel(id, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["models"] }); setEditing(null); },
  });
  const del = useMutation({
    mutationFn: deleteModel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models"] }),
  });

  return (
    <PageShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">Models</h1>
        <button className="btn-primary" onClick={() => setEditing("new")}>+ New Model</button>
      </div>

      {editing && (
        <ModelForm
          initial={editing === "new" ? undefined : editing}
          providers={providerIds}
          onSave={(v) => editing === "new" ? create.mutate(v) : update.mutate({ id: (editing as Model).id, body: v })}
          onCancel={() => setEditing(null)}
        />
      )}

      {isLoading && <p className="text-muted-foreground">Loading…</p>}

      <div className="bg-card border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              {["ID", "Provider", "Native ID", "Context", "Weight", "Flags", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {models.map((m) => (
              <tr key={m.id} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-4 py-2 font-mono text-xs">{m.id}</td>
                <td className="px-4 py-2 text-xs">{m.provider_id}</td>
                <td className="px-4 py-2 font-mono text-xs">{m.native_id}</td>
                <td className="px-4 py-2 text-xs">{m.context_len.toLocaleString()}</td>
                <td className="px-4 py-2 text-xs">{m.weight}</td>
                <td className="px-4 py-2 flex gap-1">
                  {m.is_active && <span className="badge badge-green">active</span>}
                  {m.supports_streaming && <span className="badge badge-blue">stream</span>}
                  {m.supports_vision && <span className="badge badge-purple">vision</span>}
                </td>
                <td className="px-4 py-2 flex gap-2 justify-end">
                  <button className="btn-ghost text-xs" onClick={() => setEditing(m)}>Edit</button>
                  <button className="btn-ghost text-xs text-destructive" onClick={() => { if (confirm(`Delete ${m.id}?`)) del.mutate(m.id); }}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PageShell>
  );
}
