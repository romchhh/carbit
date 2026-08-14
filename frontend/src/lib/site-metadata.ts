import type { Metadata } from "next";
import { LANDING_IMAGES } from "@/lib/brand-assets";

export const SITE_NAME = "Carbit";
export const SITE_OG_IMAGE_PATH = LANDING_IMAGES.hero;

const DEFAULT_SITE_URL = "https://carbit.info";

/** Title / description під запити: пошук авто, AUTO.RIA, OLX, моніторинг оголошень. */
export const HOME_TITLE = "Пошук авто на AUTO.RIA, OLX і Telegram";
export const HOME_DESCRIPTION =
  "Пошук авто з пробігом по AUTO.RIA, OLX, Імперія Авто, uDrive і Telegram в одному місці. Моніторинг оголошень і миттєві сповіщення — знаходь авто раніше за конкурентів.";

const OG_IMAGE = {
  url: SITE_OG_IMAGE_PATH,
  width: 1536,
  height: 1024,
  alt: "Carbit — пошук авто на AUTO.RIA, OLX і Telegram",
} as const;

const BRAND_TITLE_SUFFIX = new RegExp(`\\s*[—|\\-]\\s*${SITE_NAME}\\s*$`, "i");

export function resolveSiteUrl(): string {
  return (process.env.NEXT_PUBLIC_SITE_URL?.trim() || DEFAULT_SITE_URL).replace(/\/$/, "");
}

/** Прибирає «— Carbit» з кінця, щоб шаблон title не задвоював бренд. */
export function stripBrandFromTitle(title: string): string {
  return title.replace(BRAND_TITLE_SUFFIX, "").trim();
}

export function withBrandTitle(pageTitle: string): string {
  const clean = stripBrandFromTitle(pageTitle);
  return clean ? `${clean} — ${SITE_NAME}` : SITE_NAME;
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

/**
 * Мета для внутрішніх сторінок.
 * Передавай короткий title без «— Carbit» (шаблон layout додасть бренд один раз).
 */
export function pageMetadata(
  title: string,
  description: string,
  overrides: Metadata = {},
): Metadata {
  const pageTitle = stripBrandFromTitle(title);
  const fullTitle = withBrandTitle(pageTitle);
  const { openGraph: ogOverride, twitter: twOverride, alternates, ...rest } = overrides;
  const canonical =
    typeof alternates?.canonical === "string" ? alternates.canonical : undefined;

  return siteMetadata({
    title: pageTitle,
    description,
    alternates: {
      ...alternates,
      canonical,
    },
    openGraph: {
      title: fullTitle,
      description,
      ...(canonical ? { url: canonical } : {}),
      ...ogOverride,
    },
    twitter: { title: fullTitle, description, ...twOverride },
    ...rest,
  });
}

export const DEFAULT_SITE_METADATA = siteMetadata({
  title: {
    default: withBrandTitle(HOME_TITLE),
    template: `%s — ${SITE_NAME}`,
  },
  description: HOME_DESCRIPTION,
  keywords: [
    "пошук авто",
    "авто з пробігом",
    "оголошення авто",
    "AUTO.RIA",
    "OLX авто",
    "моніторинг оголошень",
    "агрегатор авто",
    "Telegram авто",
    "Carbit",
  ],
  authors: [{ name: SITE_NAME, url: resolveSiteUrl() }],
  creator: SITE_NAME,
  publisher: SITE_NAME,
  category: "automotive",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: SITE_NAME,
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
    title: withBrandTitle(HOME_TITLE),
    description: HOME_DESCRIPTION,
    url: "/",
  },
  twitter: {
    title: withBrandTitle(HOME_TITLE),
    description: HOME_DESCRIPTION,
  },
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
});
