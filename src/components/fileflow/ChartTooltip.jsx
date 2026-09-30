// Shared premium tooltip for recharts charts.
export default function ChartTooltip({ active, payload, label, unit = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-strong rounded-lg px-3 py-2 shadow-xl">
      {label != null && (
        <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
      )}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-[12.5px]">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: p.color || p.payload?.fill }}
          />
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-mono font-semibold text-foreground">
            {typeof p.value === "number" ? p.value.toLocaleString("en-US") : p.value}
            {unit}
          </span>
        </div>
      ))}
    </div>
  );
}