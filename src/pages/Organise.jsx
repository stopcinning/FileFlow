import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  UploadCloud,
  FileText,
  Image as ImageIcon,
  Film,
  Music,
  Archive,
  Code2,
  PenTool,
  File,
  Sparkles,
  Check,
  Loader2,
  Trash2,
  FolderInput,
  Wand2,
  X,
  FileArchive,
} from "lucide-react";
import Topbar, { TopbarButton } from "@/components/layout/Topbar";
import PageContainer, { SectionTitle } from "@/components/fileflow/PageContainer";
import { folders, suggestedActions, typeMeta } from "@/lib/fileflowData";
import { cn } from "@/lib/utils";

const typeIcons = {
  documents: FileText,
  images: ImageIcon,
  video: Film,
  audio: Music,
  archives: Archive,
  code: Code2,
  design: PenTool,
  unknown: File,
};

const sampleDrops = [
  { name: "Q3-Financial-Report-final-v4.pdf", type: "documents", size: "4.2 MB" },
  { name: "Screenshot 2026-09-30 at 09.18.42.png", type: "images", size: "1.8 MB" },
  { name: "render-export-04k.mov", type: "video", size: "184 MB" },
  { name: "track-master-07.wav", type: "audio", size: "38 MB" },
  { name: "api-handler.ts", type: "code", size: "4 KB" },
  { name: "moodboard-v2.fig", type: "design", size: "12 MB" },
  { name: "invoice_08412.pdf", type: "documents", size: "118 KB" },
  { name: "backup-archive-sep.zip", type: "archives", size: "640 MB" },
];

const detectType = (name) => {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  const map = {
    pdf: "documents", doc: "documents", docx: "documents", txt: "documents",
    png: "images", jpg: "images", jpeg: "images", heic: "images", gif: "images", webp: "images",
    mp4: "video", mov: "video", avi: "video",
    mp3: "audio", wav: "audio", flac: "audio",
    zip: "archives", tar: "archives", gz: "archives", rar: "archives",
    js: "code", ts: "code", jsx: "code", tsx: "code", py: "code",
    fig: "design", sketch: "design", ai: "design",
  };
  return map[ext] || "unknown";
};

export default function Organise() {
  const [pending, setPending] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [done, setDone] = useState([]);
  const inputRef = useRef(null);
  const dragDepth = useRef(0);

  const addFiles = useCallback((files) => {
    const next = files.map((f, i) => {
      const type = detectType(f.name);
      return {
        id: `${Date.now()}-${i}`,
        name: f.name,
        size: f.size ? `${(f.size / 1024 / 1024).toFixed(1)} MB` : "—",
        type,
        target: targetFor(type),
      };
    });
    setPending((p) => [...p, ...next]);
  }, []);

  const addSample = () => addFiles(sampleDrops.map((s) => ({ name: s.name, size: parseFloat(s) * 1024 * 1024 || 1024 })));

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    dragDepth.current = 0;
    const files = Array.from(e.dataTransfer?.files || []);
    if (files.length) addFiles(files);
    else addSample();
  };

  const removePending = (id) => setPending((p) => p.filter((x) => x.id !== id));

  const organiseAll = () => {
    if (!pending.length) return;
    setProcessing(true);
    setTimeout(() => {
      setDone(pending);
      setPending([]);
      setProcessing(false);
      setTimeout(() => setDone([]), 2200);
    }, 1800);
  };

  return (
    <>
      <Topbar
        title="Smart Organise"
        subtitle="Drop files — FileFlow detects, sorts, and files them automatically"
        actions={
          <TopbarButton icon={Wand2} primary onClick={organiseAll}>
            {processing ? "Organising…" : `Organise ${pending.length || ""}`.trim()}
          </TopbarButton>
        }
      />
      <PageContainer>
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
          {/* Drop zone + pending tray */}
          <div className="xl:col-span-2">
            <div
              onDragEnter={(e) => {
                e.preventDefault();
                dragDepth.current++;
                setDragging(true);
              }}
              onDragOver={(e) => e.preventDefault()}
              onDragLeave={(e) => {
                e.preventDefault();
                dragDepth.current--;
                if (dragDepth.current <= 0) setDragging(false);
              }}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className={cn(
                "group relative flex h-[260px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition-all",
                dragging
                  ? "border-primary bg-primary/10 glow-primary"
                  : "border-border bg-card/40 hover:border-primary/40 hover:bg-card/60"
              )}
            >
              <input
                ref={inputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => {
                  addFiles(Array.from(e.target.files || []));
                  e.target.value = "";
                }}
              />
              <motion.div
                animate={{ y: dragging ? -4 : 0, scale: dragging ? 1.08 : 1 }}
                className="flex h-16 w-16 items-center justify-center rounded-2xl border border-primary/30 bg-primary/10 text-primary"
              >
                <UploadCloud className="h-7 w-7" />
              </motion.div>
              <h3 className="mt-4 font-heading text-[16px] font-semibold text-foreground">
                {dragging ? "Release to add files" : "Drop files to organise"}
              </h3>
              <p className="mt-1 text-[13px] text-muted-foreground">
                or <span className="text-primary">browse</span> — FileFlow detects the category instantly
              </p>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  addSample();
                }}
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-border bg-background/60 px-3 py-1.5 text-[12px] font-medium text-foreground transition-colors hover:border-primary/40"
              >
                <Sparkles className="h-3.5 w-3.5 text-primary" /> Add sample files
              </button>
            </div>

            {/* Pending tray */}
            <div className="mt-4">
              <SectionTitle action={<span className="text-[12px] text-muted-foreground">{pending.length} pending</span>}>
                Queue
              </SectionTitle>
              {pending.length === 0 && done.length === 0 ? (
                <EmptyQueue />
              ) : (
                <div className="space-y-2">
                  <AnimatePresence mode="popLayout">
                    {pending.map((f) => {
                      const Icon = typeIcons[f.type] || File;
                      const meta = typeMeta(f.type);
                      return (
                        <motion.div
                          key={f.id}
                          layout
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          className="card-elevated flex items-center gap-3 rounded-xl p-3"
                        >
                          <div
                            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border"
                            style={{ background: `${meta.color}18`, borderColor: `${meta.color}30`, color: meta.color }}
                          >
                            <Icon className="h-5 w-5" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-[13px] font-medium text-foreground">{f.name}</p>
                            <p className="text-[11.5px] text-muted-foreground">
                              {meta.label} · {f.size} → <span className="font-mono text-primary">{f.target}</span>
                            </p>
                          </div>
                          <button
                            onClick={() => removePending(f.id)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>

                  {done.length > 0 && (
                    <div className="flex items-center justify-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/5 py-3 text-[13px] font-medium text-emerald-400">
                      <Check className="h-4 w-4" /> {done.length} files organised into their folders
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right column: folders + suggested actions */}
          <div className="space-y-5">
            <div>
              <SectionTitle>Folder map</SectionTitle>
              <div className="grid grid-cols-2 gap-2.5">
                {folders.map((d, i) => {
                  const Icon = typeIcons[d.key] || File;
                  return (
                    <motion.div
                      key={d.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="card-elevated card-elevated-hover rounded-xl p-3.5"
                    >
                      <div
                        className="flex h-9 w-9 items-center justify-center rounded-lg"
                        style={{ background: `${d.color}18`, color: d.color }}
                      >
                        <Icon className="h-5 w-5" />
                      </div>
                      <p className="mt-2.5 truncate text-[13px] font-semibold text-foreground">{d.name}</p>
                      <p className="font-mono text-[11px] text-muted-foreground">
                        {d.count.toLocaleString()} · {d.size}
                      </p>
                    </motion.div>
                  );
                })}
              </div>
            </div>

            <div>
              <SectionTitle>Suggested actions</SectionTitle>
              <div className="space-y-2">
                {suggestedActions.map((s, i) => {
                  const Icon = { Archive, CopyX: Trash2, Sparkles, FileArchive }[s.icon] || Sparkles;
                  const toneCls =
                    s.tone === "warning"
                      ? "border-amber-500/30 text-amber-400"
                      : s.tone === "positive"
                      ? "border-emerald-500/30 text-emerald-400"
                      : "border-primary/30 text-primary";
                  return (
                    <motion.button
                      key={s.id}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 + i * 0.06 }}
                      className={cn(
                        "card-elevated card-elevated-hover flex w-full items-center gap-3 rounded-xl border-l-2 p-3 text-left",
                        toneCls
                      )}
                    >
                      <Icon className="h-4.5 w-4.5 shrink-0" />
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-medium text-foreground">{s.title}</p>
                        <p className="truncate text-[11.5px] text-muted-foreground">{s.detail}</p>
                      </div>
                    </motion.button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </PageContainer>
    </>
  );
}

function targetFor(type) {
  const map = {
    documents: "/Documents",
    images: "/Images/Screenshots",
    video: "/Video/Exports",
    audio: "/Audio/Masters",
    archives: "/Archives",
    code: "/Projects",
    design: "/Design",
    unknown: "/Unsorted",
  };
  return map[type] || "/Unsorted";
}

function EmptyQueue() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted/40 text-muted-foreground">
        <FolderInput className="h-6 w-6" />
      </div>
      <p className="mt-3 text-[13px] font-medium text-foreground">Your queue is empty</p>
      <p className="mt-1 max-w-[240px] text-[12px] text-muted-foreground">
        Drop files above or add a sample batch to see FileFlow sort them into the right folders.
      </p>
    </div>
  );
}