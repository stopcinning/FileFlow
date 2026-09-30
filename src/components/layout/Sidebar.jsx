import { NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  FolderTree,
  BarChart3,
  Workflow,
  Settings,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Logo from "@/components/fileflow/Logo";
import { summary } from "@/lib/fileflowData";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/organise", label: "Smart Organise", icon: FolderTree },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/rules", label: "Rules Engine", icon: Workflow },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  const usedPct = Math.round((summary.storageUsed / summary.storageTotal) * 100);

  return (
    <aside className="flex h-full w-[248px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar/80 backdrop-blur-xl">
      {/* Brand */}
      <div className="flex h-16 items-center gap-2.5 px-5">
        <Logo size={30} />
        <div className="leading-none">
          <div className="font-heading text-[15px] font-bold tracking-tight text-foreground">
            FileFlow
          </div>
          <div className="mt-1 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground/70">
            Organise everything
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="scrollbar-thin mt-2 flex-1 overflow-y-auto px-3">
        <div className="px-2 pb-2 pt-1 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/50">
          Workspace
        </div>
        <ul className="space-y-0.5">
          {nav.map((item) => {
            const active =
              item.end
                ? location.pathname === item.to
                : location.pathname.startsWith(item.to);
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13.5px] font-medium transition-colors",
                    active
                      ? "text-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 -z-0 rounded-lg border border-primary/30 bg-primary/10"
                      transition={{ type: "spring", stiffness: 380, damping: 32 }}
                    />
                  )}
                  {active && (
                    <span className="absolute left-0 top-1/2 h-5 -translate-y-1/2 rounded-r-full bg-primary" style={{ width: 2.5 }} />
                  )}
                  <item.icon
                    className={cn(
                      "relative z-10 h-[18px] w-[18px] transition-colors",
                      active ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                    )}
                  />
                  <span className="relative z-10">{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>

        {/* Upgrade card */}
        <div className="relative mt-6 overflow-hidden rounded-xl border border-primary/20 p-4">
          <div className="absolute inset-0 gradient-brand-soft" />
          <div className="absolute -right-6 -top-6 h-20 w-20 rounded-full bg-primary/30 blur-2xl" />
          <div className="relative">
            <div className="flex items-center gap-1.5 text-primary">
              <Sparkles className="h-4 w-4" />
              <span className="text-[12px] font-semibold">Pro tip</span>
            </div>
            <p className="mt-1.5 text-[12px] leading-relaxed text-muted-foreground">
              Schedule weekly auto-organise to keep your library tidy without lifting a finger.
            </p>
            <button className="mt-3 inline-flex items-center gap-1 text-[12px] font-semibold text-primary hover:gap-1.5 transition-all">
              Enable schedule <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </nav>

      {/* Storage widget */}
      <div className="border-t border-sidebar-border p-3">
        <div className="rounded-lg bg-sidebar-accent/50 p-3">
          <div className="flex items-center justify-between text-[11.5px]">
            <span className="font-medium text-muted-foreground">Storage</span>
            <span className="font-mono font-medium text-foreground">{usedPct}%</span>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-border">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${usedPct}%` }}
              transition={{ duration: 1, ease: "easeOut", delay: 0.3 }}
              className="h-full rounded-full bg-gradient-to-r from-primary to-chart-5"
            />
          </div>
          <div className="mt-1.5 font-mono text-[10.5px] text-muted-foreground/70">
            {summary.storageUsed} GB / {summary.storageTotal} GB
          </div>
        </div>
      </div>
    </aside>
  );
}