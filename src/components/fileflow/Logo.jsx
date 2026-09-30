// FileFlow brand mark — layered flowing sheets forming an abstract "F".
export default function Logo({ size = 32, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="ff-grad" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop stopColor="#8B7CFF" />
          <stop offset="0.5" stopColor="#A855F7" />
          <stop offset="1" stopColor="#22D3EE" />
        </linearGradient>
        <linearGradient id="ff-grad-2" x1="36" y1="4" x2="4" y2="36" gradientUnits="userSpaceOnUse">
          <stop stopColor="#22D3EE" stopOpacity="0.9" />
          <stop offset="1" stopColor="#8B7CFF" stopOpacity="0.2" />
        </linearGradient>
      </defs>
      <rect x="3" y="3" width="34" height="34" rx="9" fill="url(#ff-grad)" fillOpacity="0.16" />
      <rect x="3" y="3" width="34" height="34" rx="9" stroke="url(#ff-grad)" strokeOpacity="0.4" strokeWidth="1" />
      <path d="M13 11h14M13 11v18M13 20h10" stroke="url(#ff-grad)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M27 11l4 4-4 4" stroke="url(#ff-grad-2)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}