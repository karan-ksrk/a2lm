"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listRateLimits,
  listModels,
  upsertRateLimit,
  deleteRateLimit,
  type RateLimit,
  type RateLimitIn,
} from "@/lib/api";
import { PageShell } from "@/components/page-shell";

function RateLimitForm({
  initial,
  modelPairs,
  onSave,
  onCancel,
}: {
  initial?: RateLimit;
  modelPairs: { provider_id: string; native_id: string; label: string }[];
  onSave: (provider_id: string, native_id: string, v: RateLimitIn) => void;
  onCancel: () => void;
}) {
  const [pid, setPid] = useState(initial?.provider_id ?? modelPairs[0]?.provider_id ?? "");
  const [nid, setNid] = useState(initial?.native_id ?? modelPairs[0]?.native_id ?? "");
  const [rpm, setRpm] = useState(initial?.rpm ?? 60);
  const [daily, setDaily] = useState(initial?.daily ?? 1000);
  const [notes, setNotes] = useState(initial?.notes ?? "");

  const selectedKey = `${pid}||${nid}`;

  return (
    <div className="bg-card border rounded-lg p-6 space-y-4 mb-6">
      <h2 className="font-semibold">{initial ? "Edit Rate Limit" : "New Rate Limit"}</h2>
      <div className="grid grid-cols-3 gap-4">
        {initial ? (
          <>
            <div>
              <label className="field-label">Provider</label>
              <input className="input" value={pid} disabled />
            </div>
            <div>
              <label className="field-label">Native Model ID</label>
              <input className="input" value={nid} disabled />
            </div>
          </>
        ) : (
          <div className="col-span-2">
            <label className="field-label">Model</label>
            <select
              className="input"
              value={selectedKey}
              onChange={(e) => {
                const [p, n] = e.target.value.split("||");
                setPid(p);
                setNid(n);
              }}
            >
              {modelPairs.map((m) => (
                <option key={`${m.provider_id}||${m.native_id}`} value={`${m.provider_id}||${m.native_id}`}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="field-label">RPM</label>
          <input className="input" type="number" value={rpm} onChange={(e) => setRpm(Number(e.target.value))} />
        </div>
        <div>
          <label className="field-label">Daily</label>
          <input className="input" type="number" value={daily} onChange={(e) => setDaily(Number(e.target.value))} />
        </div>
        <div className="col-span-2">
          <label className="field-label">Notes</label>
          <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex gap-2">
        <button className="btn-primary" onClick={() => onSave(pid, nid, { rpm, daily, notes: notes || undefined })}>Save</button>
        <button className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function RateLimitsPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<RateLimit | null | "new">(null);

  const { data: limits = [], isLoading } = useQuery({ queryKey: ["rate-limits"], queryFn: listRateLimits });
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: listModels });

  const modelPairs = models.map((m) => ({
    provider_id: m.provider_id,
    native_id: m.native_id,
    label: `${m.provider_id} / ${m.native_id}`,
  }));

  const upsert = useMutation({
    mutationFn: ({ pid, nid, body }: { pid: string; nid: string; body: RateLimitIn }) =>
      upsertRateLimit(pid, nid, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["rate-limits"] }); setEditing(null); },
  });
  const del = useMutation({
    mutationFn: ({ pid, nid }: { pid: string; nid: string }) => deleteRateLimit(pid, nid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rate-limits"] }),
  });

  return (
    <PageShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">Rate Limits</h1>
        <button className="btn-primary" onClick={() => setEditing("new")}>+ New Rate Limit</button>
      </div>

      {editing && (
        <RateLimitForm
          initial={editing === "new" ? undefined : editing}
          modelPairs={modelPairs}
          onSave={(pid, nid, body) => upsert.mutate({ pid, nid, body })}
          onCancel={() => setEditing(null)}
        />
      )}

      {isLoading && <p className="text-muted-foreground">Loading…</p>}

      <div className="bg-card border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              {["Provider", "Native Model ID", "RPM", "Daily", "Notes", "Updated", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {limits.map((rl) => (
              <tr key={rl.id} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-4 py-2 text-xs">{rl.provider_id}</td>
                <td className="px-4 py-2 font-mono text-xs">{rl.native_id}</td>
                <td className="px-4 py-2">{rl.rpm}</td>
                <td className="px-4 py-2">{rl.daily.toLocaleString()}</td>
                <td className="px-4 py-2 text-xs text-muted-foreground">{rl.notes ?? "—"}</td>
                <td className="px-4 py-2 text-xs text-muted-foreground">
                  {new Date(rl.updated_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-2 flex gap-2 justify-end">
                  <button className="btn-ghost text-xs" onClick={() => setEditing(rl)}>Edit</button>
                  <button
                    className="btn-ghost text-xs text-destructive"
                    onClick={() => { if (confirm(`Delete rate limit for ${rl.native_id}?`)) del.mutate({ pid: rl.provider_id, nid: rl.native_id }); }}
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
