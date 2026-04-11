"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";
import { clsx } from "clsx";

const links = [
  { href: "/providers", label: "Providers" },
  { href: "/models", label: "Models" },
  { href: "/aliases", label: "Aliases" },
  { href: "/rate-limits", label: "Rate Limits" },
  { href: "/status", label: "Status" },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <nav className="border-b bg-card">
      <div className="mx-auto max-w-7xl px-4 flex h-14 items-center gap-6">
        <span className="font-bold text-sm tracking-tight">A2LM</span>
        <div className="flex items-center gap-1 flex-1">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                "px-3 py-1.5 rounded-md text-sm transition-colors",
                pathname.startsWith(href)
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              {label}
            </Link>
          ))}
        </div>
        <button
          onClick={logout}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
