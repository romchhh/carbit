type PwaAppIconProps = {
  size?: number;
  className?: string;
};

export function PwaAppIcon({ size = 48, className = "" }: PwaAppIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <rect width="512" height="512" rx="112" fill="#0A0C0E" />
      <rect x="32" y="32" width="448" height="448" rx="96" fill="url(#carbit-bg)" />
      <path
        d="M96 332H416M128 332V288L168 244H208L248 204H312L352 244H392L432 288V332"
        stroke="white"
        strokeWidth="28"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M248 208H312L352 248H224L248 208Z" fill="#00C896" />
      <circle cx="168" cy="332" r="36" stroke="white" strokeWidth="24" />
      <circle cx="344" cy="332" r="36" stroke="white" strokeWidth="24" />
      <circle cx="168" cy="332" r="14" fill="#00C896" />
      <circle cx="344" cy="332" r="14" fill="#00C896" />
      <defs>
        <linearGradient id="carbit-bg" x1="80" y1="48" x2="432" y2="464" gradientUnits="userSpaceOnUse">
          <stop stopColor="#111418" />
          <stop offset="1" stopColor="#1A1F26" />
        </linearGradient>
      </defs>
    </svg>
  );
}
