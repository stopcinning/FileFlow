// FileFlow — central mock data layer. Realistic figures so the product
// reads like one with real users and history.

export const fileTypes = [
  { key: "documents", label: "Documents", ext: "pdf, docx, pages", color: "hsl(245 85% 68%)", icon: "FileText", count: 4821, size: 18.4 },
  { key: "images", label: "Images", ext: "png, jpg, heic", color: "hsl(322 85% 66%)", icon: "Image", count: 6102, size: 41.2 },
  { key: "video", label: "Video", ext: "mp4, mov", color: "hsl(190 95% 56%)", icon: "Film", count: 318, size: 124.7 },
  { key: "audio", label: "Audio", ext: "mp3, wav, flac", color: "hsl(152 65% 52%)", icon: "Music", count: 744, size: 9.8 },
  { key: "archives", label: "Archives", ext: "zip, tar, gz", color: "hsl(38 95% 60%)", icon: "Archive", count: 156, size: 6.1 },
  { key: "code", label: "Code", ext: "js, ts, py", color: "hsl(280 85% 66%)", icon: "Code2", count: 2331, size: 1.2 },
  { key: "design", label: "Design", ext: "fig, sketch, ai", color: "hsl(0 0% 70%)", icon: "PenTool", count: 412, size: 3.4 },
];

export const summary = {
  totalFiles: 14884,
  filesProcessed: 14209,
  storageSaved: 38.6, // GB
  duplicatesFound: 1294,
  storageUsed: 184.2,
  storageTotal: 512,
  efficiency: 94,
  rulesActive: 17,
  avgOrganiseTime: 1.4, // seconds per file
};

// 12 weeks of activity for trend graphs
export const weeklyActivity = [
  { week: "W1", processed: 612, saved: 1.8, organised: 540 },
  { week: "W2", processed: 744, saved: 2.1, organised: 690 },
  { week: "W3", processed: 588, saved: 1.6, organised: 522 },
  { week: "W4", processed: 901, saved: 2.9, organised: 845 },
  { week: "W5", processed: 832, saved: 2.4, organised: 778 },
  { week: "W6", processed: 1024, saved: 3.1, organised: 980 },
  { week: "W7", processed: 778, saved: 2.2, organised: 712 },
  { week: "W8", processed: 1156, saved: 3.6, organised: 1090 },
  { week: "W9", processed: 988, saved: 2.8, organised: 920 },
  { week: "W10", processed: 1289, saved: 4.1, organised: 1212 },
  { week: "W11", processed: 1102, saved: 3.4, organised: 1040 },
  { week: "W12", processed: 1395, saved: 4.6, organised: 1320 },
];

// last 7 days for the dashboard mini trend
export const dailyActivity = [
  { day: "Mon", processed: 184, organised: 170 },
  { day: "Tue", processed: 212, organised: 198 },
  { day: "Wed", processed: 156, organised: 150 },
  { day: "Thu", processed: 248, organised: 230 },
  { day: "Fri", processed: 302, organised: 288 },
  { day: "Sat", processed: 96, organised: 88 },
  { day: "Sun", processed: 134, organised: 120 },
];

export const activityFeed = [
  { id: 1, type: "organise", title: "Moved 248 screenshots to /Images/Screenshots", source: "Rule: Screenshots → Images", time: "2m ago", icon: "FolderInput" },
  { id: 2, type: "duplicate", title: "Found 12 duplicate files in Downloads", source: "Saved 412 MB", time: "11m ago", icon: "CopyX" },
  { id: 3, type: "rename", title: "Renamed 84 files using date-prefix convention", source: "Rule: ISO Date Prefix", time: "38m ago", icon: "TextCursorInput" },
  { id: 4, type: "archive", title: "Archived 31 old invoices to /Finance/2024", source: "Rule: Yearly Archive", time: "1h ago", icon: "Archive" },
  { id: 5, type: "tag", title: "Tagged 16 design files as 'Client: Northwind'", source: "Rule: Client Tagging", time: "2h ago", icon: "Tag" },
  { id: 6, type: "compress", title: "Compressed 9 video files", source: "Saved 2.1 GB", time: "3h ago", icon: "FileArchive" },
  { id: 7, type: "organise", title: "Sorted 412 code assets into /Projects", source: "Rule: Dev Workspace", time: "5h ago", icon: "FolderInput" },
  { id: 8, type: "backup", title: "Cloud backup completed for /Documents", source: "1,204 files synced", time: "8h ago", icon: "CloudUpload" },
];

export const insights = [
  { id: 1, tone: "positive", title: "Storage trending down", body: "You've reclaimed 12.4 GB this week — 34% above your weekly average.", icon: "TrendingDown" },
  { id: 2, tone: "warning", title: "Downloads folder is bloated", body: "318 files haven't been touched in 90+ days. Consider archiving.", icon: "AlertTriangle" },
  { id: 3, tone: "neutral", title: "Rule opportunity", body: "412 screenshots share a naming pattern. A rule could auto-file them.", icon: "Sparkles" },
];

export const recentFiles = [
  { id: "f1", name: "Q3-Financial-Report-final-v4.pdf", type: "documents", size: "4.2 MB", folder: "/Finance/Reports", date: "Today, 14:21", status: "organised" },
  { id: "f2", name: "Screenshot 2026-09-30 at 09.18.42.png", type: "images", size: "1.8 MB", folder: "/Images/Screenshots", date: "Today, 09:18", status: "organised" },
  { id: "f3", name: "client-brief-northwind.docx", type: "documents", size: "822 KB", folder: "/Clients/Northwind", date: "Today, 08:04", status: "organised" },
  { id: "f4", name: "render-export-04k.mov", type: "video", size: "184 MB", folder: "/Projects/Render", date: "Yesterday, 22:40", status: "pending" },
  { id: "f5", name: "invoice_08412.pdf", type: "documents", size: "118 KB", folder: "/Finance/Invoices", date: "Yesterday, 17:12", status: "organised" },
  { id: "f6", name: "track-master-07.wav", type: "audio", size: "38 MB", folder: "/Audio/Masters", date: "Yesterday, 15:30", status: "pending" },
  { id: "f7", name: "api-handler.ts", type: "code", size: "4 KB", folder: "/Projects/FileFlow", date: "Yesterday, 11:02", status: "organised" },
  { id: "f8", name: "moodboard-v2.fig", type: "design", size: "12 MB", folder: "/Design/Moodboards", date: "29 Sep, 19:44", status: "organised" },
];

export const folders = [
  { id: "d1", name: "Documents", count: 4821, size: "18.4 GB", color: "hsl(245 85% 68%)", icon: "FileText" },
  { id: "d2", name: "Images", count: 6102, size: "41.2 GB", color: "hsl(322 85% 66%)", icon: "Image" },
  { id: "d3", name: "Video", count: 318, size: "124.7 GB", color: "hsl(190 95% 56%)", icon: "Film" },
  { id: "d4", name: "Audio", count: 744, size: "9.8 GB", color: "hsl(152 65% 52%)", icon: "Music" },
  { id: "d5", name: "Projects", count: 2331, size: "1.2 GB", color: "hsl(280 85% 66%)", icon: "Code2" },
  { id: "d6", name: "Archives", count: 156, size: "6.1 GB", color: "hsl(38 95% 60%)", icon: "Archive" },
];

export const ruleTemplates = [
  { id: "t1", name: "Screenshots → Images", desc: "Move all screenshot files into a dated Images subfolder.", trigger: "name matches 'Screenshot*'", action: "move → /Images/Screenshots/{date}", category: "images", runs: 1284, icon: "Camera" },
  { id: "t2", name: "ISO Date Prefix", desc: "Rename files with a consistent YYYY-MM-DD prefix.", trigger: "any file", action: "rename → {date}_{name}", category: "documents", runs: 4021, icon: "Calendar" },
  { id: "t3", name: "Yearly Archive", desc: "Archive files older than 12 months by year.", trigger: "modified > 365d", action: "move → /Archive/{year}", category: "archives", runs: 318, icon: "Archive" },
  { id: "t4", name: "Duplicate Sweeper", desc: "Detect and quarantine byte-identical duplicates.", trigger: "hash collision", action: "move → /Duplicates", category: "system", runs: 1294, icon: "CopyX" },
  { id: "t5", name: "Client Tagging", desc: "Tag files matching client keyword patterns.", trigger: "name contains client", action: "tag → client:{name}", category: "documents", runs: 612, icon: "Tag" },
  { id: "t6", name: "Dev Workspace", desc: "Route code & assets into a structured project tree.", trigger: "ext in js,ts,py", action: "move → /Projects/{repo}", category: "code", runs: 2331, icon: "Code2" },
];

export const customRules = [
  { id: "r1", name: "Screenshots → Images", enabled: true, trigger: "name matches 'Screenshot*'", action: "move → /Images/Screenshots/{date}", runs: 1284, lastRun: "2m ago", category: "images" },
  { id: "r2", name: "ISO Date Prefix", enabled: true, trigger: "any file", action: "rename → {date}_{name}", runs: 4021, lastRun: "38m ago", category: "documents" },
  { id: "r3", name: "Yearly Archive", enabled: true, trigger: "modified > 365d", action: "move → /Archive/{year}", runs: 318, lastRun: "1h ago", category: "archives" },
  { id: "r4", name: "Duplicate Sweeper", enabled: true, trigger: "hash collision", action: "move → /Duplicates", runs: 1294, lastRun: "11m ago", category: "system" },
  { id: "r5", name: "Client Tagging", enabled: false, trigger: "name contains client", action: "tag → client:{name}", runs: 612, lastRun: "2h ago", category: "documents" },
  { id: "r6", name: "Dev Workspace", enabled: true, trigger: "ext in js,ts,py", action: "move → /Projects/{repo}", runs: 2331, lastRun: "5h ago", category: "code" },
  { id: "r7", name: "Large Video Compress", enabled: false, trigger: "size > 100MB & ext in mp4,mov", action: "compress → h265", runs: 9, lastRun: "3h ago", category: "video" },
];

export const categories = [
  { id: "c1", name: "Documents", color: "hsl(245 85% 68%)", count: 4821 },
  { id: "c2", name: "Images", color: "hsl(322 85% 66%)", count: 6102 },
  { id: "c3", name: "Video", color: "hsl(190 95% 56%)", count: 318 },
  { id: "c4", name: "Audio", color: "hsl(152 65% 52%)", count: 744 },
  { id: "c5", name: "Code", color: "hsl(280 85% 66%)", count: 2331 },
  { id: "c6", name: "Archives", color: "hsl(38 95% 60%)", count: 156 },
  { id: "c7", name: "Design", color: "hsl(0 0% 70%)", count: 412 },
];

export const suggestedActions = [
  { id: "s1", title: "Archive 318 stale downloads", detail: "90+ days untouched · 4.2 GB", icon: "Archive", tone: "warning" },
  { id: "s2", title: "Merge 12 duplicate files", detail: "Reclaim 412 MB instantly", icon: "CopyX", tone: "positive" },
  { id: "s3", title: "Create rule for screenshots", detail: "412 files match the pattern", icon: "Sparkles", tone: "neutral" },
  { id: "s4", title: "Compress 9 large videos", detail: "Save up to 2.1 GB", icon: "FileArchive", tone: "neutral" },
];

export const formatNumber = (n) =>
  n >= 1000 ? n.toLocaleString("en-US") : String(n);

export const typeMeta = (key) =>
  fileTypes.find((t) => t.key === key) || { label: key, color: "hsl(0 0% 70%)", icon: "File" };