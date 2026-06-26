import { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

const icon = (path: React.ReactNode, viewBox = "0 0 24 24") =>
  function Icon({ size = 20, className, ...props }: IconProps) {
    return (
      <svg
        width={size}
        height={size}
        viewBox={viewBox}
        fill="none"
        className={className}
        {...props}
      >
        {path}
      </svg>
    );
  };

export const IconSearch = icon(
  <>
    <circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M15.5 15.5L21 21" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconBell = icon(
  <>
    <path d="M6 10a6 6 0 1 1 12 0c0 3.5 1.5 5 2 6H4c.5-1 2-2.5 2-6Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    <path d="M10 20a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconTelegram = icon(
  <>
    <path d="M21 4L2 11.5l7 1L11 19l2-4 4 3 4-14Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    <path d="M9 12.5l8-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconArrowRight = icon(
  <>
    <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconArrowLeft = icon(
  <>
    <path d="M19 12H5M11 6l-6 6 6 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconArrowDown = icon(
  <>
    <path d="M12 5v14M5 12l7 7 7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconCheck = icon(
  <>
    <path d="M5 12l5 5L19 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconX = icon(
  <>
    <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconPlus = icon(
  <>
    <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconPause = icon(
  <>
    <rect x="6" y="5" width="4" height="14" rx="1" stroke="currentColor" strokeWidth="1.6"/>
    <rect x="14" y="5" width="4" height="14" rx="1" stroke="currentColor" strokeWidth="1.6"/>
  </>
);

export const IconPlay = icon(
  <>
    <path d="M6 4l14 8-14 8V4Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
  </>
);

export const IconEdit = icon(
  <>
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    <path d="M18.5 2.5a2 2 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
  </>
);

export const IconTrash = icon(
  <>
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconChart = icon(
  <>
    <path d="M3 20V8l5 5 4-8 4 5 4-7v17" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconFilter = icon(
  <>
    <path d="M3 5h18M7 10h10M11 15h2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconClock = icon(
  <>
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M12 7v5l3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconLocation = icon(
  <>
    <path d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7Z" stroke="currentColor" strokeWidth="1.6"/>
    <circle cx="12" cy="9" r="2.5" stroke="currentColor" strokeWidth="1.4"/>
  </>
);

export const IconGlobe = icon(
  <>
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" stroke="currentColor" strokeWidth="1.6"/>
  </>
);

export const IconShield = icon(
  <>
    <path d="M12 3L4 7v5c0 4.4 3.4 8.5 8 9.5 4.6-1 8-5.1 8-9.5V7l-8-4Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </>
);

export const IconZap = icon(
  <>
    <path d="M13 2L4 14h8l-1 8 9-12h-8l1-8Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
  </>
);

export const IconCreditCard = icon(
  <>
    <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M2 10h20" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M6 15h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconGear = icon(
  <>
    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M12 2v2M12 20v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2 12h2M20 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconHeart = icon(
  <>
    <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1 7.8 7.8 7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
  </>
);

export const IconEye = icon(
  <>
    <path d="M1 12S5 5 12 5s11 7 11 7-4 7-11 7S1 12 1 12Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6"/>
  </>
);

export const IconLock = icon(
  <>
    <rect x="5" y="10" width="14" height="11" rx="2" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M8 10V7a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    <circle cx="12" cy="15.5" r="1.5" fill="currentColor"/>
  </>
);

export const IconMail = icon(
  <>
    <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M2 8l10 6 10-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconDownload = icon(
  <>
    <path d="M12 3v12M8 11l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M3 17v2a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);

export const IconShare = icon(
  <>
    <path d="M8 12l8-5v10l-8-5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    <path d="M4 6v12a2 2 0 0 0 2 2h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </>
);
