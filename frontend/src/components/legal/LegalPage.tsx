import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

type LegalSection = {
  title: string;
  content: React.ReactNode;
};

type LegalPageProps = {
  title: string;
  subtitle: string;
  updated: string;
  sections: LegalSection[];
};

export function LegalPage({ title, subtitle, updated, sections }: LegalPageProps) {
  return (
    <>
      <Header />
      <main className="bg-white min-h-screen">
        <section className="border-b border-border/60 bg-surface/40">
          <div className="max-w-[800px] mx-auto px-5 sm:px-8 pt-28 pb-12">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-[13px] text-muted hover:text-emerald-dark transition-colors mb-8"
            >
              ← На головну
            </Link>
            <h1 className="text-[36px] sm:text-[48px] font-black tracking-[-0.03em] text-ink leading-tight">
              {title}
            </h1>
            <p className="mt-4 text-[16px] sm:text-[17px] text-muted leading-relaxed">{subtitle}</p>
            <p className="mt-3 text-[13px] text-muted/70">Останнє оновлення: {updated}</p>
          </div>
        </section>

        <article className="max-w-[800px] mx-auto px-5 sm:px-8 py-12 sm:py-16">
          <div className="space-y-10">
            {sections.map(({ title: sectionTitle, content }) => (
              <section key={sectionTitle} className="scroll-mt-24">
                <h2 className="text-[22px] sm:text-[24px] font-bold text-ink tracking-tight mb-4">
                  {sectionTitle}
                </h2>
                <div className="text-[15px] text-muted leading-[1.75] space-y-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-2 [&_a]:text-emerald-dark [&_a]:font-medium [&_a]:hover:underline">
                  {content}
                </div>
              </section>
            ))}
          </div>

          <div className="mt-16 pt-8 border-t border-border/60 flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between">
            <p className="text-[14px] text-muted">
              Питання? Напишіть на{" "}
              <a href="mailto:info@13vplus.com">info@13vplus.com</a>
            </p>
            <div className="flex gap-4 text-[13px]">
              <Link href="/terms" className="text-ink font-medium hover:text-emerald-dark transition-colors">
                Умови
              </Link>
              <Link href="/privacy" className="text-ink font-medium hover:text-emerald-dark transition-colors">
                Конфіденційність
              </Link>
            </div>
          </div>
        </article>
      </main>
      <Footer />
    </>
  );
}
