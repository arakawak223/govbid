"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/", label: "案件一覧" },
  { href: "/results", label: "落札結果" },
];

export default function NavTabs() {
  const pathname = usePathname();

  return (
    <nav className="flex gap-1">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
              active
                ? "bg-blue-50 text-blue-700"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
