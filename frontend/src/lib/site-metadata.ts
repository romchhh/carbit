import type { Metadata } from "next";
import { LANDING_IMAGES } from "@/lib/brand-assets";

export const SITE_NAME = "Carbit";
export const SITE_OG_IMAGE_PATH = LANDING_IMAGES.hero;

const DEFAULT_SITE_URL = "https://carbit.info";
const DEFAULT_DESCRIPTION =
  "AUTO.RIA, OLX і Telegram в одному пошуку. Знаходь авто раніше за конкурентів.";

const OG_IMAGE = {
  url: SITE_OG_IMAGE_PATH,
  width: 1536,
  height: 1024,
  alt: "Carbit — агрегатор авторинку: AUTO.RIA, OLX і Telegram в одному пошуку",
} as const;

export function resolveSiteUrl(): string {
  return (process.env.NEXT_PUBLIC_SITE_URL?.trim() || DEFAULT_SITE_URL).replace(/\/$/, "");
}

/** OG/Twitter preview — hero з головної, не лого. */
export function siteMetadata(overrides: Metadata = {}): Metadata {
  const { openGraph: ogOverride, twitter: twOverride, ...rest } = overrides;

  return {
    metadataBase: new URL(resolveSiteUrl()),
    ...rest,
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      locale: "uk_UA",
      ...ogOverride,
      images: ogOverride?.images ?? [OG_IMAGE],
    },
    twitter: {
      card: "summary_large_image",
      ...twOverride,
      images: twOverride?.images ?? [SITE_OG_IMAGE_PATH],
    },
  };
}

export function pageMetadata(title: string, description: string, overrides: Metadata = {}): Metadata {
  return siteMetadata({
    title,
    description,
    openGraph: { title, description },
    twitter: { title, description },
    ...overrides,
  });
}

export const DEFAULT_SITE_METADATA = siteMetadata({
  title: {
    default: "Carbit — Агрегатор авторинку",
    template: "%s — Carbit",
  },
  description: DEFAULT_DESCRIPTION,
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: "Carbit",
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  openGraph: {
    title: "Carbit — Агрегатор авторинку",
    description: DEFAULT_DESCRIPTION,
  },
  twitter: {
    title: "Carbit — Агрегатор авторинку",
    description: DEFAULT_DESCRIPTION,
  },
});
