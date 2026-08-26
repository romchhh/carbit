import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Пошук авто",
  robots: { index: false, follow: false },
};

export default function PublicSearchLayout({ children }: { children: React.ReactNode }) {
  return children;
}
