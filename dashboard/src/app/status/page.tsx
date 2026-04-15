"use client";

import { useQuery } from "@tanstack/react-query";
import { PageShell } from "@/components/page-shell";
import { listProviders, listModels, listAliases, listRateLimits } from "@/lib/api";


function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-card border rounded-lg p-5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

export default function StatusPage() {
  const { data: providers = [] } = useQuery({ queryKey: ["providers"], queryFn: listProviders });
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: listModels });
  const { data: aliases = [] } = useQuery({ queryKey: ["aliases"], queryFn: listAliases });
  const { data: rateLimits = [] } = useQuery({ queryKey: ["rate-limits"], queryFn: listRateLimits });

  const activeProviders = providers.filter((p) => p.is_active).length;
  const activeModels = models.filter((m) => m.is_active).length;
  const activeAliases = aliases.filter((a) => a.is_active).length;
  const aliasNames = new Set(aliases.map((a) => a.alias_name)).size;

  return (
    <PageShell>
      <h1 className="text-xl font-bold mb-6">Status</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Providers" value={activeProviders} sub={`${providers.length} total`} />
        <StatCard label="Models" value={activeModels} sub={`${models.length} total`} />
        <StatCard label="Alias Groups" value={aliasNames} sub={`${activeAliases} active entries`} />
        <StatCard label="Rate Limits" value={rateLimits.length} sub="configured" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b font-medium text-sm">Active Providers</div>
          <table className="w-full text-sm">
            <tbody>
              {providers.filter((p) => p.is_active).map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="px-4 py-2 font-medium">{p.display_name}</td>
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{p.adapter_class}</td>
                  <td className="px-4 py-2 text-right text-xs">
                    {models.filter((m) => m.provider_id === p.id && m.is_active).length} models
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-card border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b font-medium text-sm">Alias Groups</div>
          <table className="w-full text-sm">
            <tbody>
              {Array.from(new Set(aliases.map((a) => a.alias_name))).map((name) => {
                const entries = aliases.filter((a) => a.alias_name === name && a.is_active);
                return (
                  <tr key={name} className="border-b last:border-0">
                    <td className="px-4 py-2 font-mono text-sm">{name}</td>
                    <td className="px-4 py-2 text-xs text-muted-foreground">
                      {entries.map((e) => e.provider_id).join(", ")}
                    </td>
                    <td className="px-4 py-2 text-right text-xs">{entries.length} backends</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </PageShell>
  );
}
