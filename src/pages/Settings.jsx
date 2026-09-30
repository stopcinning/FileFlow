import { useState } from "react";
import { motion } from "framer-motion";
import {
  Palette,
  Tags,
  Power,
  DatabaseBackup,
  Bell,
  Plus,
  Check,
  CloudUpload,
  Moon,
  Sun,
  Monitor,
  Trash2,
  RotateCw,
} from "lucide-react";
import Topbar from "@/components/layout/Topbar";
import PageContainer, { SectionTitle } from "@/components/fileflow/PageContainer";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { categories as initialCategories } from "@/lib/fileflowData";
import { cn } from "@/lib/utils";

const accents = [
  { name: "Indigo", value: "245 85% 68%" },
  { name: "Violet", value: "270 85% 66%" },
  { name: "Magenta", value: "322 85% 66%" },
  { name: "Cyan", value: "190 95% 56%" },
  { name: "Emerald", value: "152 65% 52%" },
  { name: "Amber", value: "38 95% 60%" },
];

export default function Settings() {
  const [accent, setAccent] = useState("245 85% 68%");
  const [theme, setTheme] = useState("dark");
  const [categories, setCategories] = useState(initialCategories);
  const [newCat, setNewCat] = useState("");
  const [startup, setStartup] = useState({ launchOnStart: true, minimiseToTray: false, autoOrganise: true });
  const [backup, setBackup] = useState({ autoBackup: true, frequency: 30, includeArchives: true });
  const [notif, setNotif] = useState({ organiseComplete: true, duplicates: true, weeklyDigest: false, storageAlerts: true });
  const [backingUp, setBackingUp] = useState(false);
  const [backedUp, setBackedUp] = useState(false);

  const applyAccent = (v) => {
    setAccent(v);
    document.documentElement.style.setProperty("--primary", v);
    document.documentElement.style.setProperty("--ring", v);
  };

  const addCategory = () => {
    if (!newCat.trim()) return;
    setCategories((c) => [...c, { id: `c${Date.now()}`, name: newCat.trim(), color: "hsl(245 85% 68%)", count: 0 }]);
    setNewCat("");
  };
  const removeCategory = (id) => setCategories((c) => c.filter((x) => x.id !== id));

  const runBackup = () => {
    setBackingUp(true);
    setBackedUp(false);
    setTimeout(() => {
      setBackingUp(false);
      setBackedUp(true);
      setTimeout(() => setBackedUp(false), 2400);
    }, 1800);
  };

  return (
    <>
      <Topbar title="Settings" subtitle="Personalise FileFlow and tune how it runs" />
      <PageContainer className="max-w-[920px]">
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {/* Appearance */}
          <SettingCard icon={Palette} title="Appearance" desc="Theme and accent colour">
            <div className="mt-1">
              <p className="mb-2 text-[12px] font-medium text-muted-foreground">Theme</p>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { k: "dark", l: "Dark", icon: Moon },
                  { k: "light", l: "Light", icon: Sun },
                  { k: "system", l: "System", icon: Monitor },
                ].map((t) => (
                  <button
                    key={t.k}
                    onClick={() => setTheme(t.k)}
                    className={cn(
                      "flex items-center justify-center gap-1.5 rounded-lg border py-2.5 text-[12.5px] font-medium transition-colors",
                      theme === t.k
                        ? "border-primary/50 bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <t.icon className="h-4 w-4" /> {t.l}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-4">
              <p className="mb-2 text-[12px] font-medium text-muted-foreground">Accent colour</p>
              <div className="flex flex-wrap gap-2">
                {accents.map((a) => (
                  <button
                    key={a.name}
                    onClick={() => applyAccent(a.value)}
                    title={a.name}
                    className={cn(
                      "relative h-8 w-8 rounded-full transition-transform hover:scale-110",
                      accent === a.value && "ring-2 ring-offset-2 ring-offset-card"
                    )}
                    style={{ background: `hsl(${a.value})`, boxShadow: accent === a.value ? `0 0 0 2px hsl(${a.value})` : undefined }}
                  >
                    {accent === a.value && (
                      <Check className="absolute inset-0 m-auto h-4 w-4 text-white" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </SettingCard>

          {/* Startup */}
          <SettingCard icon={Power} title="Startup" desc="How FileFlow launches">
            <ToggleRow label="Launch on system start" desc="Open FileFlow when you log in" checked={startup.launchOnStart} onChange={(v) => setStartup((s) => ({ ...s, launchOnStart: v }))} />
            <ToggleRow label="Minimise to tray" desc="Keep running in the menu bar" checked={startup.minimiseToTray} onChange={(v) => setStartup((s) => ({ ...s, minimiseToTray: v }))} />
            <ToggleRow label="Auto-organise on launch" desc="Run all active rules immediately" checked={startup.autoOrganise} onChange={(v) => setStartup((s) => ({ ...s, autoOrganise: v }))} />
          </SettingCard>

          {/* Custom categories */}
          <SettingCard icon={Tags} title="Custom categories" desc="Labels FileFlow uses to sort files">
            <div className="flex flex-wrap gap-2">
              {categories.map((c) => (
                <motion.span
                  key={c.id}
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="group inline-flex items-center gap-1.5 rounded-lg border border-border bg-muted/40 py-1 pl-2 pr-1.5 text-[12px] font-medium"
                >
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
                  {c.name}
                  <button
                    onClick={() => removeCategory(c.id)}
                    className="flex h-4 w-4 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </motion.span>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2">
              <input
                value={newCat}
                onChange={(e) => setNewCat(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addCategory()}
                placeholder="Add a category…"
                className="h-9 flex-1 rounded-lg border border-border bg-card/60 px-3 text-[13px] text-foreground placeholder:text-muted-foreground/70 focus:border-primary/50 focus:outline-none"
              />
              <button
                onClick={addCategory}
                className="flex h-9 items-center gap-1 rounded-lg bg-primary px-3 text-[13px] font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
              >
                <Plus className="h-4 w-4" /> Add
              </button>
            </div>
          </SettingCard>

          {/* Backup */}
          <SettingCard icon={DatabaseBackup} title="Backup" desc="Keep your library safe">
            <ToggleRow label="Automatic backup" desc="Back up organised files on a schedule" checked={backup.autoBackup} onChange={(v) => setBackup((b) => ({ ...b, autoBackup: v }))} />
            <div className="py-3">
              <div className="flex items-center justify-between text-[12.5px]">
                <span className="font-medium text-foreground">Backup frequency</span>
                <span className="font-mono text-muted-foreground">every {backup.frequency} min</span>
              </div>
              <Slider
                value={[backup.frequency]}
                onValueChange={(v) => setBackup((b) => ({ ...b, frequency: v[0] }))}
                min={5}
                max={120}
                step={5}
                className="mt-3"
              />
            </div>
            <ToggleRow label="Include archives" desc="Back up the /Archives folder too" checked={backup.includeArchives} onChange={(v) => setBackup((b) => ({ ...b, includeArchives: v }))} />
            <button
              onClick={runBackup}
              disabled={backingUp}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-card/60 py-2.5 text-[13px] font-semibold text-foreground transition-colors hover:border-primary/40 disabled:opacity-60"
            >
              {backingUp ? (
                <><RotateCw className="h-4 w-4 animate-spin" /> Backing up…</>
              ) : backedUp ? (
                <><Check className="h-4 w-4 text-emerald-400" /> Backup complete</>
              ) : (
                <><CloudUpload className="h-4 w-4" /> Back up now</>
              )}
            </button>
          </SettingCard>

          {/* Notifications */}
          <SettingCard icon={Bell} title="Notifications" desc="What FileFlow tells you about" className="md:col-span-2">
            <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
              <ToggleRow label="Organisation complete" desc="When a batch finishes" checked={notif.organiseComplete} onChange={(v) => setNotif((n) => ({ ...n, organiseComplete: v }))} />
              <ToggleRow label="Duplicates detected" desc="When duplicates are found" checked={notif.duplicates} onChange={(v) => setNotif((n) => ({ ...n, duplicates: v }))} />
              <ToggleRow label="Weekly digest" desc="A summary every Monday" checked={notif.weeklyDigest} onChange={(v) => setNotif((n) => ({ ...n, weeklyDigest: v }))} />
              <ToggleRow label="Storage alerts" desc="When you near your limit" checked={notif.storageAlerts} onChange={(v) => setNotif((n) => ({ ...n, storageAlerts: v }))} />
            </div>
          </SettingCard>
        </div>

        <p className="mt-6 text-center text-[11.5px] text-muted-foreground/60">
          FileFlow v2.4.1 · Organise everything. Automatically.
        </p>
      </PageContainer>
    </>
  );
}

function SettingCard({ icon: Icon, title, desc, children, className = "" }) {
  return (
    <div className={cn("card-elevated rounded-xl p-5", className)}>
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="font-heading text-[14.5px] font-semibold text-foreground">{title}</h2>
          <p className="text-[12px] text-muted-foreground">{desc}</p>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function ToggleRow({ label, desc, checked, onChange }) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <div>
        <p className="text-[13px] font-medium text-foreground">{label}</p>
        <p className="text-[11.5px] text-muted-foreground">{desc}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}