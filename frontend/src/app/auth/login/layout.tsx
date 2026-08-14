import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site-metadata";

export const metadata: Metadata = pageMetadata(
  "Вхід і реєстрація",
  "Увійдіть у Carbit, щоб шукати авто на AUTO.RIA, OLX і Telegram та отримувати сповіщення про нові оголошення.",
  { alternates: { canonical: "/auth/login" } },
);

export default function AuthLoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
