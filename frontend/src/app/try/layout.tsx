import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Безкоштовний пошук авто",
  robots: { index: false, follow: false },
};

export default function GuestTryLayout({ children }: { children: React.ReactNode }) {
  return children;
}
