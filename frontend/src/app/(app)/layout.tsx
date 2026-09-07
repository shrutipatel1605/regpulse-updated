"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/shell/AppShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return <AppShell routeKey={pathname}>{children}</AppShell>;
}
