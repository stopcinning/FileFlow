import { useState } from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Gauge,
  Files,
  HardDrive,
  Activity,
  TrendingUp,
  Clock,
  Filter,
} from "lucide-react";
import Topbar from "@/components/layout/Topbar";
import PageContainer, { SectionTitle } from "@/components/fileflow/PageContainer";
import StatCard from "@/components/fileflow/StatCard";
import AnimatedCounter from "@/components/fileflow/AnimatedCounter";
import ChartTooltip from "@/components/fileflow/ChartTooltip";
import { fileTypes, weeklyActivity, summary } from "@/lib/fileflowData";

const rangeTabs = [
  { key: "4w", label: "4 weeks" },
  { key: "12w", label: "12 weeks" },
  { key: "ytd", label: "Year to date" },
];

const efficiencyData = [{ name: "Efficiency", value: summary.efficiency, fill: "hsl(245 85% 68%)" }];

export default function Analytics() {
  const [range, setRange] = useState("12w");
  const data =
    range === "4w" ? weeklyActivity.slice(-4) : range === "12w" ? weeklyActivity : weeklyActivity;

  return (
    <>
      <Topbar
        title="Analytics"
        subtitle="Understand how your library behaves over time"
        actions={
          <div className="flex h-9 items-center rounded-lg border border-border bg-card/60 p-0.5">
            {rangeTabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setRange(t.key)}
                className={
                  range === t.key
                    ? "rounded-md bg-primary px-2.5 py-1 text-[12px] font-semibold text-primary-foreground"
                    : "px-2.5 py-1 text-[12px] font-medium text-muted-foreground hover:text-foreground"
                }
              >
                {t.label}
              </button>
            ))}
          </div>
        }
      />
      <PageContainer>
        {/* Highlights */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard index={0} label="Efficiency score" icon={Gauge} accent="hsl(245 85% 68%)" value={<AnimatedCounter value={summary.efficiency} />} unit="%" delta="+3 pts" />
          <StatCard index={1} label="Total files" icon={Files} accent="hsl(190 95% 56%)" value={<AnimatedCounter value={summary.totalFiles} />} delta="+1,204" />
          <StatCard index={2} label="Storage used" icon={HardDrive} accent="hsl(322 85% 66%)" value={<AnimatedCounter value={summary.storageUsed} decimals={1} />} unit="GB" delta="-12.4 GB" deltaTone="down" />
          <StatCard index={3} label="Avg. organise time" icon={Clock} accent="hsl(152 65% 52%)" value={<AnimatedCounter value={summary.avgOrganiseTime} decimals={1} />} unit="s/file" delta="-0.3s" deltaTone="down" />
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
          {/* Efficiency radial */}
          <div className="card-elevated rounded-xl p-5">
            <h2 className="font-heading text-[15px] font-semibold text-foreground">Organisation efficiency</h2>
            <p className="text-[12.5px] text-muted-foreground">Composite score across all rules</p>
            <div className="relative mt-2 h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  innerRadius="72%"
                  outerRadius="100%"
                  data={efficiencyData}
                  startAngle={90}
                  endAngle={-270}
                >
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar background={{ fill: "hsl(var(--muted))" }} dataKey="value" cornerRadius={20} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-heading text-[34px] font-bold text-foreground">
                  <AnimatedCounter value={summary.efficiency} />%
                </span>
                <span className="text-[12px] text-emerald-400">Excellent</span>
              </div>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              {[
                { l: "Accuracy", v: "96%" },
                { l: "Coverage", v: "88%" },
                { l: "Speed", v: "98%" },
              ].map((s) => (
                <div key={s.l} className="rounded-lg bg-muted/40 py-2">
                  <div className="font-mono text-[15px] font-semibold text-foreground">{s.v}</div>
                  <div className="text-[10.5px] text-muted-foreground">{s.l}</div>
                </div>
              ))}
            </div>
          </div>

          {/* File type breakdown */}
          <div className="card-elevated rounded-xl p-5 xl:col-span-2">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-heading text-[15px] font-semibold text-foreground">File type breakdown</h2>
                <p className="text-[12.5px] text-muted-foreground">File count by category</p>
              </div>
              <Filter className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-4 h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={fileTypes} margin={{ top: 4, right: 6, left: -16, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.5} />
                  <XAxis dataKey="label" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted) / 0.4)" }} />
                  <Bar dataKey="count" name="Files" radius={[6, 6, 0, 0]} maxBarSize={48}>
                    {fileTypes.map((t) => (
                      <Cell key={t.key} fill={t.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Historical activity + storage trend */}
        <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="card-elevated rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-heading text-[15px] font-semibold text-foreground">Historical activity</h2>
                <p className="text-[12.5px] text-muted-foreground">Processed vs. organised per week</p>
              </div>
              <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400">
                <TrendingUp className="h-3 w-3" /> +18%
              </span>
            </div>
            <div className="mt-4 h-[230px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 4, right: 6, left: -16, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.5} />
                  <XAxis dataKey="week" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted) / 0.4)" }} />
                  <Bar dataKey="processed" name="Processed" fill="hsl(245 85% 68%)" radius={[4, 4, 0, 0]} maxBarSize={26} />
                  <Bar dataKey="organised" name="Organised" fill="hsl(190 95% 56%)" radius={[4, 4, 0, 0]} maxBarSize={26} fillOpacity={0.7} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card-elevated rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-heading text-[15px] font-semibold text-foreground">Storage reclaimed</h2>
                <p className="text-[12.5px] text-muted-foreground">GB saved through organisation</p>
              </div>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-4 h-[230px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 4, right: 6, left: -16, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.5} />
                  <XAxis dataKey="week" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
                  <Tooltip content={<ChartTooltip unit=" GB" />} cursor={{ stroke: "hsl(var(--border))" }} />
                  <Line
                    type="monotone"
                    dataKey="saved"
                    name="Saved"
                    stroke="hsl(152 65% 52%)"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: "hsl(152 65% 52%)" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </PageContainer>
    </>
  );
}