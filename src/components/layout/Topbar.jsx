import { Search, Command, Bell, Zap, FolderPlus } from "lucide-react";

export default function Topbar({ title, subtitle, actions }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-background/70 px-6 backdrop-blur-xl">
      <div className="min-w-0">
        <h1 className="truncate font-heading text-[17px] font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        {subtitle && (
          <p className="truncate text-[12.5px] text-muted-foreground">{subtitle}</p>
        )}
      </div>

      {/* Search */}
      <div className="ml-auto hidden items-center md:flex">
        <div className="group flex h-9 w-[280px] items-center gap-2 rounded-lg border border-border bg-card/60 px-3 text-muted-foreground transition-colors hover:border-primary/40 focus-within:border-primary/60">
          <Search className="h-4 w-4" />
          <input
            placeholder="Search files, folders, rules…"
            className="w-full bg-transparent text-[13px] text-foreground placeholder:text-muted-foreground/70 focus:outline-none"
          />
          <kbd className="flex items-center gap-0.5 rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {actions}
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card/60 text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground">
          <Bell className="h-[18px] w-[18px]" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
        </button>
        <div className="ml-1 flex h-9 items-center gap-2 rounded-lg border border-border bg-card/60 pl-1.5 pr-3">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-primary to-chart-5 text-[11px] font-bold text-white">
            AK
          </div>
          <div className="leading-none">
            <div className="text-[12px] font-semibold text-foreground">Alex Kerr</div>
            <div className="mt-0.5 text-[10px] text-muted-foreground">Pro plan</div>
          </div>
        </div>
      </div>
    </header>
  );
}

// Reusable primary action button used in topbars.
export function TopbarButton({ icon: Icon, children, onClick, primary }) {
  return (
    <button
      onClick={onClick}
      className={
        primary
          ? "flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-[13px] font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:bg-primary/90 hover:shadow-primary/30"
          : "flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card/60 px-3 text-[13px] font-medium text-foreground transition-colors hover:border-primary/40"
      }
    >
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

export { Zap, FolderPlus };