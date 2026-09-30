import { Outlet } from "react-router-dom";
import Sidebar from "@/components/layout/Sidebar";

// Desktop-app shell: fixed sidebar + scrollable main region.
export default function AppLayout() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* ambient gradient backdrop */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute left-1/4 top-0 h-[420px] w-[620px] -translate-x-1/2 rounded-full bg-primary/10 blur-[120px]" />
        <div className="absolute right-0 top-1/3 h-[360px] w-[460px] rounded-full bg-chart-5/8 blur-[120px]" />
        <div className="absolute bottom-0 left-1/3 h-[320px] w-[420px] rounded-full bg-chart-2/8 blur-[120px]" />
      </div>
      <Sidebar />
      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}