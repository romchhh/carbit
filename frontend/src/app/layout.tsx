import type { Metadata, Viewport } from "next";
import { Montserrat } from "next/font/google";
import { AuthProvider } from "@/contexts/AuthProvider";
import "./globals.css";

const montserrat = Montserrat({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-montserrat",
});

export const metadata: Metadata = {
  title: "Carbit — Агрегатор авторинку",
  description: "AUTO.RIA, OLX і Telegram в одному пошуку. Знаходь авто раніше за конкурентів.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: "Carbit",
    statusBarStyle: "default",
  },
  icons: {
    icon: "/icons/icon.svg",
    apple: "/icons/icon.svg",
  },
};
export const viewport: Viewport = { themeColor: "#00C896" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uk" className={montserrat.variable}>
      <body className={montserrat.className}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
