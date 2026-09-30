import { useState } from "react";
import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Files,
  HardDriveDownload,
  CopyX,
  Gauge,
  FolderInput,
  CopyX as CopyXIcon,
  TextCursorInput,
  Archive,
  Tag,
  FileArchive,
  CloudUpload,
  TrendingDown,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  Check,
  Clock,
  FolderPlus,
} from "lucide-react";
import Topbar, { TopbarButton } from "@/components/layout/Topbar";
import PageContainer, { SectionTitle } from "@/components/fileflow/PageContainer";
import StatCard from "@/components/fileflow/StatCard";
import AnimatedCounter from "@/components/fileflow/AnimatedCounter";
import ChartTooltip from "@/components/fileflow/ChartTooltip";
import {
  summary,
  dailyActivity,
  weeklyActivity,
  activityFeed,
  insights,
  recentFiles,
  fileTypes,
  typeMeta,
  formatNumber,
} from "@/lib/fileflowData";
import { cn } from "@/lib/utils";

const activityIcons = {
  FolderInput,
  CopyX: CopyXIcon,
  TextCursorInput,
  Archive,
  Tag,
  FileArchive,
  CloudUpload,
};

const insightIcons = { TrendingDown, AlertTriangle, Sparkles };
const insightTone = {
  positive: "border-emerald-500/30 bg-emerald-500/5 text-emerald-400",
  warning: "border-amber-500/30 bg-amber-500/5 text-amber-400",
  neutral: "border-primary/30 bg-primary/5 text-primary",
};

export default function Dashboard() {
  const [running, setRunning] = useState(false);

  const handleOrganise = () => {
    setRunning(true);
    setTimeout(() => setRunning(false), 2600);
  };

  return (
    <>
      <Topbar
        title="Dashboard"
        subtitle="Your library at a glance"
        actions={
          <TopbarButton icon={FolderPlus} primary onClick={handleOrganise}>
            {running ? "Organising…" : "Organise now"}
          </TopbarButton>
        }
      />
      <PageContainer>
        {/* Stat cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            index={0}
            label="Files processed"
            icon={Files}
            accent="hsl(245 85% 68%)"
            delta="+12.4%"
            value={<AnimatedCounter value={summary.filesProcessed} />}
            deltaTone="up"
          >
            <Sparkline data={dailyActivity} dataKey="processed" color="hsl(245 85% 68%)" />
          </StatCard>
          <StatCard
            index={1}
            label="Storage saved"
            icon={HardDriveDownload}
            accent="hsl(152 65% 52%)"
            delta="+4.6 GB"
            value={<AnimatedCounter value={summary.storageSaved} decimals={1} />}
            unit="GB"
            deltaTone="up"
          >
            <Sparkline data={dailyActivity} dataKey="organised" color="hsl(152 65% 52%)" />
          </StatCard>
          <StatCard
            index={2}
            label="Duplicates found"
            icon={CopyX}
            accent="hsl(322 85% 66%)"
            delta="-8.2%"
            value={<AnimatedCounter value={summary.duplicatesFound} />}
            deltaTone="down"
          >
            <Sparkline data={weeklyActivity.slice(-7)} dataKey="saved" color="hsl(322 85% 66%)" />
          </StatCard>
          <StatCard
            index={3}
            label="Efficiency score"
            icon={Gauge}
            accent="hsl(190 95% 56%)"
            delta="+3 pts"
            value={<AnimatedCounter value={summary.efficiency} />}
            unit="%"
            deltaTone="up"
          >
            <div className="flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${summary.efficiency}%` }}
                  transition={{ duration: 1.1, ease: "easeOut", delay: 0.3 }}
                  className="h-full rounded-full bg-gradient-to-r from-chart-2 to-chart-1"
                />
              </div>
              <span className="text-[11px] font-medium text-muted-foreground">Excellent</span>
            </div>
          </StatCard>
        </div>

        {/* Main grid */}
        <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
          {/* Activity chart */}
          <div className="card-elevated rounded-xl p-5 xl:col-span-2">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-heading text-[15px] font-semibold text-foreground">
                  Weekly activity
                </h2>
                <p className="text-[12.5px] text-muted-foreground">
                  Files processed & organised over the last 12 weeks
                </p>
              </div>
              <div className="flex items-center gap-4 text-[12px]">
                <Legend color="hsl(245 85% 68%)" label="Processed" />
                <Legend color="hsl(190 95% 56%)" label="Organised" />
              </div>
            </div>
            <div className="mt-4 h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={weeklyActivity} margin={{ top: 6, right: 6, left: -18, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gProc" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(245 85% 68%)" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="hsl(245 85% 68%)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gOrg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(190 95% 56%)" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="hsl(190 95% 56%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="week"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={42}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: "hsl(var(--border))" }} />
                  <Area
                    type="monotone"
                    dataKey="processed"
                    name="Processed"
                    stroke="hsl(245 85% 68%)"
                    strokeWidth={2}
                    fill="url(#gProc)"
                  />
                  <Area
                    type="monotone"
                    dataKey="organised"
                    name="Organised"
                    stroke="hsl(190 95% 56%)"
                    strokeWidth={2}
                    fill="url(#gOrg)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Storage donut */}
          <div className="card-elevated rounded-xl p-5">
            <h2 className="font-heading text-[15px] font-semibold text-foreground">
              Storage usage
            </h2>
            <p className="text-[12.5px] text-muted-foreground">By file category</p>
            <div className="relative mt-2 h-[180px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={fileTypes}
                    dataKey="size"
                    nameKey="label"
                    innerRadius={56}
                    outerRadius={80}
                    paddingAngle={2}
                    stroke="none"
                  >
                    {fileTypes.map((t) => (
                      <Cell key={t.key} fill={t.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip unit=" GB" />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-heading text-[22px] font-bold text-foreground">
                  {summary.storageUsed}
                </span>
                <span className="text-[11px] text-muted-foreground">GB used</span>
              </div>
            </div>
            <div className="mt-3 space-y-1.5">
              {fileTypes.slice(0, 4).map((t) => (
                <div key={t.key} className="flex items-center justify-between text-[12px]">
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <span className="h-2 w-2 rounded-full" style={{ background: t.color }} />
                    {t.label}
                  </span>
                  <span className="font-mono text-foreground">{t.size} GB</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Insights + activity feed */}
        <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
          <div className="space-y-3">
            <SectionTitle>Smart insights</SectionTitle>
            {insights.map((ins, i) => {
              const Icon = insightIcons[ins.icon] || Sparkles;
              return (
                <motion.div
                  key={ins.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.08 }}
                  className={cn(
                    "card-elevated rounded-xl border-l-2 p-4",
                    insightTone[ins.tone]
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    <span className="text-[13px] font-semibold text-foreground">{ins.title}</span>
                  </div>
                  <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
                    {ins.body}
                  </p>
                </motion.div>
              );
            })}
          </div>

          <div className="xl:col-span-2">
            <SectionTitle
              action={
                <button className="text-[12px] font-medium text-primary hover:underline">
                  View all
                </button>
              }
            >
              Recent activity
            </SectionTitle>
            <div className="card-elevated overflow-hidden rounded-xl">
              {activityFeed.map((a, i) => {
                const Icon = activityIcons[a.icon] || FolderInput;
                return (
                  <div
                    key={a.id}
                    className={cn(
                      "flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/30",
                      i !== activityFeed.length - 1 && "border-b border-border/60"
                    )}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/40 text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium text-foreground">{a.title}</p>
                      <p className="truncate text-[11.5px] text-muted-foreground">{a.source}</p>
                    </div>
                    <span className="shrink-0 font-mono text-[11px] text-muted-foreground/70">
                      {a.time}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Recent files */}
        <div className="mt-5">
          <SectionTitle
            action={
              <button className="inline-flex items-center gap-1 text-[12px] font-medium text-primary hover:underline">
                Open library <ArrowRight className="h-3 w-3" />
              </button>
            }
          >
            Recently organised
          </SectionTitle>
          <div className="card-elevated overflow-hidden rounded-xl">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border text-[11px] uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="hidden px-4 py-2.5 font-medium md:table-cell">Folder</th>
                  <th className="hidden px-4 py-2.5 font-medium sm:table-cell">Size</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="hidden px-4 py-2.5 text-right font-medium lg:table-cell">Date</th>
                </tr>
              </thead>
              <tbody>
                {recentFiles.map((f) => {
                  const meta = typeMeta(f.type);
                  return (
                    <tr
                      key={f.id}
                      className="border-b border-border/50 text-[13px] transition-colors last:border-0 hover:bg-muted/30"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <span
                            className="h-7 w-7 shrink-0 rounded-md border"
                            style={{
                              background: `${meta.color}18`,
                              borderColor: `${meta.color}30`,
                            }}
                          />
                          <span className="truncate font-medium text-foreground">{f.name}</span>
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 font-mono text-[12px] text-muted-foreground md:table-cell">
                        {f.folder}
                      </td>
                      <td className="hidden px-4 py-3 font-mono text-[12px] text-muted-foreground sm:table-cell">
                        {f.size}
                      </td>
                      <td className="px-4 py-3">
                        {f.status === "organised" ? (
                          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                            <Check className="h-3 w-3" /> Organised
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-400">
                            <Clock className="h-3 w-3" /> Pending
                          </span>
                        )}
                      </td>
                      <td className="hidden px-4 py-3 text-right font-mono text-[12px] text-muted-foreground lg:table-cell">
                        {f.date}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </PageContainer>
    </>
  );
}

function Legend({ color, label }) {
  return (
    <span className="flex items-center gap-1.5 text-muted-foreground">
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function Sparkline({ data, dataKey, color }) {
  return (
    <div className="h-9 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`spark-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={1.8}
            fill={`url(#spark-${dataKey})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}