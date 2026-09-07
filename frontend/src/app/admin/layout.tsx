"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

const adminNav = [
  { name: "Dashboard", href: "/admin" },
  { name: "Review", href: "/admin/review" },
  { name: "Prompts", href: "/admin/prompts" },
  { name: "Users", href: "/admin/users" },
  { name: "Circulars", href: "/admin/circulars" },
  { name: "Scraper", href: "/admin/scraper" },
  { name: "Uploads", href: "/admin/uploads" },
  { name: "Heatmap", href: "/admin/heatmap" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen">
      <aside className="w-56 border-r border-gray-200 bg-white">
        <div className="flex h-14 items-center border-b border-gray-200 px-4">
          <Link href="/admin" className="text-lg font-bold text-navy-800">
            Admin
          </Link>
          <Link href="/dashboard" className="ml-auto text-xs text-gray-500 hover:text-gray-700">
            Back
          </Link>
        </div>
        <nav className="space-y-0.5 p-2">
          {adminNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block rounded-md px-3 py-2 text-sm",
                pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href))
                  ? "bg-navy-50 font-medium text-navy-700"
                  : "text-gray-600 hover:bg-gray-50",
              )}
            >
              {item.name}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
    </div>
  );
}
