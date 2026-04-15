"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  type Provider,
  type ProviderIn,
} from "@/lib/api";
import { PageShell } from "@/components/page-shell";

const ADAPTER_OPTIONS = [
  "GroqAdapter",
  "OpenRouterAdapter",
  "GoogleAIAdapter",
  "CohereAdapter",
  "MistralAdapter",
  "TogetherAdapter",
  "NvidiaAdapter",
  "HuggingFaceAdapter",
];

function ProviderForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Provider;
  onSave: (v: ProviderIn) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState<ProviderIn>(
    initial
      ? {
          id: initial.id,
          display_name: initial.display_name,
          adapter_class: initial.adapter_class,
          base_url: initial.base_url ?? "",
          is_active: initial.is_active,
          requires_account_id: initial.requires_account_id,
        }
      : {
          id: "",
          display_name: "",
          adapter_class: "GroqAdapter",
          base_url: "",
          is_active: true,
          requires_account_id: false,
        }
  );

  return (
    <div className="bg-card border rounded-lg p-6 space-y-4 mb-6">
      <h2 className="font-semibold">{initial ? "Edit Provider" : "New Provider"}</h2>
      <div className="grid grid-cols-2 gap-4">
        <Field label="ID (slug)">
          <input
            className="input"
            value={v.id}
            disabled={!!initial}
            onChange={(e) => setV({ ...v, id: e.target.value })}
          />
        </Field>
        <Field label="Display Name">
          <input
            className="input"
            value={v.display_name}
            onChange={(e) => setV({ ...v, display_name: e.target.value })}
          />
        </Field>
        <Field label="Adapter Class">
          <select
            className="input"
            value={v.adapter_class}
            onChange={(e) => setV({ ...v, adapter_class: e.target.value })}
          >
            {ADAPTER_OPTIONS.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </Field>
        <Field label="Base URL (optional)">
          <input
            className="input"
            value={v.base_url ?? ""}
            onChange={(e) => setV({ ...v, base_url: e.target.value })}
          />
        </Field>
        <Field label="Active">
          <input
            type="checkbox"
            checked={v.is_active}
            onChange={(e) => setV({ ...v, is_active: e.target.checked })}
          />
        </Field>
        <Field label="Requires Account ID">
          <input
            type="checkbox"
            checked={v.requires_account_id}
            onChange={(e) =>
              setV({ ...v, requires_account_id: e.target.checked })
            }
          />
        </Field>
      </div>
      <div className="flex gap-2">
        <button className="btn-primary" onClick={() => onSave(v)}>
          Save
        </button>
        <button className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

export default function ProvidersPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Provider | null | "new">(null);
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["providers"],
    queryFn: listProviders,
  });

  const create = useMutation({
    mutationFn: createProvider,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["providers"] }); setEditing(null); },
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<ProviderIn> }) =>
      updateProvider(id, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["providers"] }); setEditing(null); },
  });
  const del = useMutation({
    mutationFn: deleteProvider,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["providers"] }),
  });

  function handleSave(v: ProviderIn) {
    if (editing === "new") {
      create.mutate(v);
    } else if (editing) {
      update.mutate({ id: editing.id, body: v });
    }
  }

  return (
    <PageShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">Providers</h1>
        <button className="btn-primary" onClick={() => setEditing("new")}>
          + New Provider
        </button>
      </div>

      {editing && (
        <ProviderForm
          initial={editing === "new" ? undefined : editing}
          onSave={handleSave}
          onCancel={() => setEditing(null)}
        />
      )}

      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      {error && <p className="text-destructive">{String(error)}</p>}

      <div className="bg-card border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              {["ID", "Display Name", "Adapter", "Base URL", "Active", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.id} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-4 py-2 font-mono text-xs">{p.id}</td>
                <td className="px-4 py-2">{p.display_name}</td>
                <td className="px-4 py-2 font-mono text-xs">{p.adapter_class}</td>
                <td className="px-4 py-2 text-xs text-muted-foreground">{p.base_url ?? "—"}</td>
                <td className="px-4 py-2">
                  <span className={`badge ${p.is_active ? "badge-green" : "badge-gray"}`}>
                    {p.is_active ? "active" : "inactive"}
                  </span>
                </td>
                <td className="px-4 py-2 flex gap-2 justify-end">
                  <button className="btn-ghost text-xs" onClick={() => setEditing(p)}>
                    Edit
                  </button>
                  <button
                    className="btn-ghost text-xs text-destructive"
                    onClick={() => { if (confirm(`Delete ${p.id}?`)) del.mutate(p.id); }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PageShell>
  );
}
