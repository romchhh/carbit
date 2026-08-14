import type { MetadataRoute } from "next";
import { resolveSiteUrl } from "@/lib/site-metadata";

export default function robots(): MetadataRoute.Robots {
  const base = resolveSiteUrl();

  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/llms.txt", "/humans.txt"],
        disallow: ["/app/", "/admin/", "/api/", "/auth/oauth/", "/auth/telegram/", "/auth/reset-password"],
      },
      {
        // AI crawlers — дозволяємо публічний контент і llms.txt
        userAgent: ["GPTBot", "ChatGPT-User", "Google-Extended", "anthropic-ai", "ClaudeBot", "PerplexityBot"],
        allow: ["/", "/llms.txt", "/pricing", "/payment", "/oferta", "/terms", "/privacy"],
        disallow: ["/app/", "/admin/", "/api/", "/auth/"],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
