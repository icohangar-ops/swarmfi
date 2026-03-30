"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  BarChart3,
  Landmark,
  Bot,
  Settings,
} from "lucide-react";

interface SidebarProps {
  items?: { href: string; label: string; icon: React.ElementType }[];
}

export default function Sidebar({ items }: SidebarProps) {
  const pathname = usePathname();

  const defaultItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/prediction-markets", label: "Markets", icon: BarChart3 },
    { href: "/vaults", label: "Vaults", icon: Landmark },
    { href: "/agents", label: "Agents", icon: Bot },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  const navItems = items || defaultItems;

  return (
    <aside className="hidden lg:flex flex-col w-64 min-h-screen border-r border-border bg-card/50 pt-20 px-3 py-6 fixed left-0 top-0">
      <div className="space-y-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                active
                  ? "bg-cyan-500/10 text-cyan-400 border-l-2 border-cyan-400"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
