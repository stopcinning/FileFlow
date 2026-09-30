import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { cn } from "@/lib/utils";

// Premium analytics stat card with gradient accent and trend.
export default function StatCard({
  label,
  value,
  unit,
  delta,
  deltaTone = "up",
  icon: Icon,
  accent = "hsl(245 85% 68%)",
  index = 0,
  children,
}) {
  const positive = deltaTone === "up";
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.06, ease: [0.16, 1, 0.3, 1] }}
      className="card-elevated card-elevated-hover relative overflow-hidden rounded-xl p-5"
    >
      {/* accent glow */}
      <div
        className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full opacity-30 blur-2xl"
        style={{ background: accent }}
      />
      <div className="relative flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-lg border"
            style={{
              background: `linear-gradient(135deg, ${accent}22, ${accent}08)`,
              borderColor: `${accent}40`,
            }}
          >
            <Icon className="h-5 w-5" style={{ color: accent }} />
          </div>
          <span className="text-[13px] font-medium text-muted-foreground">{label}</span>
        </div>
        {delta && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[11px] font-semibold",
              positive
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-rose-500/10 text-rose-400"
            )}
          >
            {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {delta}
          </span>
        )}
      </div>
      <div className="relative mt-4 flex items-baseline gap-1.5">
        <span className="font-heading text-[28px] font-bold tracking-tight text-foreground">
          {value}
        </span>
        {unit && <span className="text-sm font-medium text-muted-foreground">{unit}</span>}
      </div>
      {children && <div className="relative mt-3">{children}</div>}
    </motion.div>
  );
}