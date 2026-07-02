import type { Metadata, Viewport } from "next";
import { Montserrat } from "next/font/google";
import { AuthProvider } from "@/contexts/AuthProvider";
import { PwaSplash } from "@/components/pwa/PwaSplash";
import { PwaServiceWorker } from "@/components/pwa/PwaServiceWorker";
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
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};
export const viewport: Viewport = { themeColor: "#00C896" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uk" className={montserrat.variable}>
      <body className={`${montserrat.className} bg-[#EEF0F4]`}>
        <PwaSplash />
        <PwaServiceWorker />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
