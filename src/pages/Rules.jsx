import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Workflow,
  Plus,
  Zap,
  Filter,
  ArrowRight,
  FolderInput,
  Tag,
  CopyX,
  Calendar,
  Archive,
  Camera,
  Code2,
  MoreHorizontal,
  Pencil,
  Trash2,
  Play,
  Sparkles,
  GitBranch,
} from "lucide-react";
import Topbar, { TopbarButton } from "@/components/layout/Topbar";
import PageContainer, { SectionTitle } from "@/components/fileflow/PageContainer";
import { Switch } from "@/components/ui/switch";
import { customRules as initialRules, ruleTemplates, typeMeta } from "@/lib/fileflowData";
import { cn } from "@/lib/utils";

const templateIcons = { Camera, Calendar, Archive, CopyX: CopyX, Tag, Code2 };

export default function Rules() {
  const [rules, setRules] = useState(initialRules);
  const [tab, setTab] = useState("active");

  const toggle = (id) =>
    setRules((rs) => rs.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)));
  const remove = (id) => setRules((rs) => rs.filter((r) => r.id !== id));

  const activeCount = rules.filter((r) => r.enabled).length;
  const visible = tab === "active" ? rules.filter((r) => r.enabled) : rules;

  return (
    <>
      <Topbar
        title="Rules Engine"
        subtitle={`${activeCount} active automations · ${rules.length} total`}
        actions={<TopbarButton icon={Plus} primary>Create rule</TopbarButton>}
      />
      <PageContainer>
        {/* Visual workflow builder */}
        <div className="card-elevated relative overflow-hidden rounded-xl p-5">
          <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-primary/15 blur-3xl" />
          <div className="relative flex items-center justify-between">
            <div>
              <h2 className="font-heading text-[15px] font-semibold text-foreground">Workflow builder</h2>
              <p className="text-[12.5px] text-muted-foreground">
                Chain triggers, conditions, and actions into an automation
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-md border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11.5px] font-medium text-primary">
              <GitBranch className="h-3.5 w-3.5" /> Draft
            </span>
          </div>

          <div className="relative mt-5 flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
            <FlowNode
              tone="trigger"
              tag="WHEN"
              icon={Zap}
              title="New file added"
              subtitle="watches /Downloads"
            />
            <FlowConnector />
            <FlowNode
              tone="condition"
              tag="IF"
              icon={Filter}
              title="name matches Screenshot*"
              subtitle="case-insensitive"
            />
            <FlowConnector />
            <FlowNode
              tone="action"
              tag="THEN"
              icon={FolderInput}
              title="move → /Images/{date}"
              subtitle="create folder if missing"
            />
            <button className="flex items-center justify-center gap-1.5 rounded-xl border border-dashed border-border py-3 text-[12.5px] font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary lg:px-4">
              <Plus className="h-4 w-4" /> Add step
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-5 flex items-center gap-1">
          {[
            { k: "active", l: `Active (${activeCount})` },
            { k: "all", l: `All (${rules.length})` },
          ].map((t) => (
            <button
              key={t.k}
              onClick={() => setTab(t.k)}
              className={
                tab === t.k
                  ? "rounded-lg bg-card px-3 py-1.5 text-[13px] font-semibold text-foreground border border-border"
                  : "rounded-lg px-3 py-1.5 text-[13px] font-medium text-muted-foreground hover:text-foreground"
              }
            >
              {t.l}
            </button>
          ))}
        </div>

        {/* Rules list */}
        <div className="mt-3 space-y-2">
          <AnimatePresence mode="popLayout">
            {visible.map((r, i) => {
              const meta = typeMeta(r.category);
              return (
                <motion.div
                  key={r.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  transition={{ delay: i * 0.03 }}
                  className="card-elevated card-elevated-hover flex items-center gap-4 rounded-xl p-4"
                >
                  <div
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border"
                    style={{ background: `${meta.color}18`, borderColor: `${meta.color}30`, color: meta.color }}
                  >
                    <Workflow className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-[13.5px] font-semibold text-foreground">{r.name}</p>
                      <span
                        className="rounded px-1.5 py-0.5 text-[10px] font-medium"
                        style={{ background: `${meta.color}18`, color: meta.color }}
                      >
                        {meta.label}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate font-mono text-[11.5px] text-muted-foreground">
                      {r.trigger} <ArrowRight className="inline h-3 w-3" /> {r.action}
                    </p>
                  </div>
                  <div className="hidden text-right sm:block">
                    <p className="font-mono text-[12px] text-foreground">{r.runs.toLocaleString()}</p>
                    <p className="text-[10.5px] text-muted-foreground">runs · {r.lastRun}</p>
                  </div>
                  <Switch checked={r.enabled} onCheckedChange={() => toggle(r.id)} />
                  <div className="flex items-center gap-1">
                    <button className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-primary">
                      <Play className="h-4 w-4" />
                    </button>
                    <button className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => remove(r.id)}
                      className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>

        {/* Templates */}
        <div className="mt-7">
          <SectionTitle action={<span className="text-[12px] text-muted-foreground">Start from a template</span>}>
            Rule templates
          </SectionTitle>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {ruleTemplates.map((t, i) => {
              const Icon = templateIcons[t.icon] || Sparkles;
              const meta = typeMeta(t.category);
              return (
                <motion.div
                  key={t.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="card-elevated card-elevated-hover group flex flex-col rounded-xl p-4"
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className="flex h-9 w-9 items-center justify-center rounded-lg"
                      style={{ background: `${meta.color}18`, color: meta.color }}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <p className="text-[13.5px] font-semibold text-foreground">{t.name}</p>
                  </div>
                  <p className="mt-2.5 flex-1 text-[12.5px] leading-relaxed text-muted-foreground">{t.desc}</p>
                  <div className="mt-3 rounded-lg bg-muted/40 px-2.5 py-1.5 font-mono text-[10.5px] text-muted-foreground">
                    {t.trigger}
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {t.runs.toLocaleString()} runs
                    </span>
                    <button className="inline-flex items-center gap-1 text-[12px] font-semibold text-primary opacity-80 transition-opacity group-hover:opacity-100">
                      Use template <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </PageContainer>
    </>
  );
}

function FlowNode({ tone, tag, icon: Icon, title, subtitle }) {
  const tones = {
    trigger: "border-amber-500/30 bg-amber-500/5 text-amber-400",
    condition: "border-primary/30 bg-primary/5 text-primary",
    action: "border-emerald-500/30 bg-emerald-500/5 text-emerald-400",
  };
  return (
    <div className="flex-1 rounded-xl border border-border bg-card/60 p-3.5">
      <div className={cn("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-bold tracking-wide", tones[tone])}>
        <Icon className="h-3 w-3" /> {tag}
      </div>
      <p className="mt-2 text-[13px] font-semibold text-foreground">{title}</p>
      <p className="text-[11.5px] text-muted-foreground">{subtitle}</p>
    </div>
  );
}

function FlowConnector() {
  return (
    <div className="flex items-center justify-center text-muted-foreground/50 lg:-mx-1">
      <ArrowRight className="h-4 w-4" />
    </div>
  );
}