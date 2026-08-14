import { FULL_LOGO_SRC, LANDING_IMAGES } from "@/lib/brand-assets";
import { CARBIT_FAQ_ITEMS, type FaqItem } from "@/lib/faq-items";
import { PRICING_PLANS, SUPPORT_EMAIL } from "@/lib/pricing-plans";
import {
  HOME_DESCRIPTION,
  HOME_TITLE,
  SITE_NAME,
  resolveSiteUrl,
  withBrandTitle,
} from "@/lib/site-metadata";

const OPERATOR_NAME = "ФОП Білоус Олександр Володимирович";

function absoluteUrl(path: string): string {
  const base = resolveSiteUrl();
  if (path.startsWith("http")) return path;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export function organizationJsonLd() {
  const base = resolveSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${base}/#organization`,
    name: SITE_NAME,
    legalName: OPERATOR_NAME,
    url: base,
    logo: {
      "@type": "ImageObject",
      url: absoluteUrl(FULL_LOGO_SRC),
    },
    image: absoluteUrl(LANDING_IMAGES.hero),
    email: SUPPORT_EMAIL,
    description: HOME_DESCRIPTION,
    address: {
      "@type": "PostalAddress",
      streetAddress: "вул. Урлівська, 20, кв. 79",
      addressLocality: "Київ",
      postalCode: "02055",
      addressCountry: "UA",
    },
    sameAs: [
      "https://www.instagram.com/carbit.info",
      "https://www.tiktok.com/@carbit.info",
    ],
    contactPoint: {
      "@type": "ContactPoint",
      contactType: "customer support",
      email: SUPPORT_EMAIL,
      availableLanguage: ["uk", "ru"],
    },
  };
}

/** Продукт / SaaS: агрегатор + підписка на моніторинг авторинку. */
export function productJsonLd() {
  const base = resolveSiteUrl();
  const paid = PRICING_PLANS.filter(p => p.id !== "free");
  const prices = paid.map(plan => Number(plan.price.replace(/\s/g, "").replace(",", ".")));
  const offers = paid.map(plan => ({
    "@type": "Offer",
    name: plan.name,
    description: plan.description,
    price: plan.price.replace(/\s/g, ""),
    priceCurrency: "UAH",
    url: absoluteUrl("/pricing"),
    availability: "https://schema.org/InStock",
    priceValidUntil: new Date(new Date().getFullYear() + 1, 11, 31).toISOString().slice(0, 10),
  }));

  return {
    "@context": "https://schema.org",
    "@type": ["SoftwareApplication", "Product"],
    "@id": `${base}/#product`,
    name: SITE_NAME,
    applicationCategory: "BusinessApplication",
    applicationSubCategory: "Automotive marketplace aggregator",
    operatingSystem: "Web",
    url: base,
    image: absoluteUrl(LANDING_IMAGES.hero),
    description: HOME_DESCRIPTION,
    brand: {
      "@type": "Brand",
      name: SITE_NAME,
    },
    provider: {
      "@id": `${base}/#organization`,
    },
    offers: {
      "@type": "AggregateOffer",
      url: absoluteUrl("/pricing"),
      priceCurrency: "UAH",
      lowPrice: String(Math.min(...prices)),
      highPrice: String(Math.max(...prices)),
      offerCount: String(offers.length),
      availability: "https://schema.org/InStock",
      offers,
    },
    featureList: [
      "Пошук авто по AUTO.RIA, OLX, Імперія Авто, uDrive і Telegram",
      "Моніторинг оголошень авторинку",
      "Миттєві сповіщення в Telegram",
      "Анти-дубль оголошень",
    ],
  };
}

export function websiteJsonLd() {
  const base = resolveSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${base}/#website`,
    name: SITE_NAME,
    url: base,
    description: HOME_DESCRIPTION,
    inLanguage: "uk-UA",
    publisher: {
      "@id": `${base}/#organization`,
    },
  };
}

export function faqPageJsonLd(items: readonly FaqItem[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map(item => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
  };
}

export function faqJsonLd() {
  return faqPageJsonLd(CARBIT_FAQ_ITEMS);
}

export function breadcrumbJsonLd(items: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: absoluteUrl(item.path),
    })),
  };
}

export function videoObjectJsonLd() {
  const base = resolveSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "VideoObject",
    name: "Як шукати авто в Carbit",
    description:
      "Коротка відеоінструкція: пошук і моніторинг авто оголошень на AUTO.RIA, OLX і Telegram.",
    thumbnailUrl: absoluteUrl(LANDING_IMAGES.hero),
    contentUrl: absoluteUrl("/video-instructions.mp4"),
    embedUrl: absoluteUrl("/"),
    uploadDate: "2026-01-15",
    inLanguage: "uk-UA",
    publisher: {
      "@id": `${base}/#organization`,
    },
  };
}

export function homeWebPageJsonLd() {
  const base = resolveSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": `${base}/#webpage`,
    url: base,
    name: withBrandTitle(HOME_TITLE),
    description: HOME_DESCRIPTION,
    isPartOf: { "@id": `${base}/#website` },
    about: { "@id": `${base}/#product` },
    primaryImageOfPage: absoluteUrl(LANDING_IMAGES.hero),
    inLanguage: "uk-UA",
  };
}
