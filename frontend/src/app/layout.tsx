import type { Metadata, Viewport } from "next";
import { Montserrat } from "next/font/google";
import { AuthProvider } from "@/contexts/AuthProvider";
import { PwaSplash } from "@/components/pwa/PwaSplash";
import { PwaServiceWorker } from "@/components/pwa/PwaServiceWorker";
import { DEFAULT_SITE_METADATA } from "@/lib/site-metadata";
import "./globals.css";

const montserrat = Montserrat({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-montserrat",
});

export const metadata: Metadata = DEFAULT_SITE_METADATA;
export const viewport: Viewport = {
  themeColor: "#00C896",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uk" className={`${montserrat.variable} h-full`}>
      <body className={`${montserrat.className} h-full min-h-[100dvh] bg-white`}>
        <PwaSplash />
        <PwaServiceWorker />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
