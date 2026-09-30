import { motion } from "framer-motion";

// Consistent page container with staggered entrance.
export default function PageContainer({ children, className = "" }) {
  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className={`mx-auto max-w-[1280px] px-6 py-6 lg:px-8 ${className}`}
      >
        {children}
      </motion.div>
    </div>
  );
}

export function SectionTitle({ children, action }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="font-heading text-[13px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {children}
      </h2>
      {action}
    </div>
  );
}