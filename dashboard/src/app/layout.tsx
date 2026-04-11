import type { Metadata } from "next";
import "./globals.css";
import { ReactQueryProvider } from "@/lib/query-client";

export const metadata: Metadata = {
  title: "A2LM Dashboard",
  description: "Admin dashboard for the A2LM Gateway",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </body>
    </html>
  );
}
