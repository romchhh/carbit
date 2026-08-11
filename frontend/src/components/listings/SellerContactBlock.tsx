import type { ReactNode } from "react";
import type { Listing } from "@/types/api";
import { IconTelegram, IconUser } from "@/components/icons";
import { Phone } from "lucide-react";
import {
  formatPhoneDisplay,
  hasSellerContact,
  resolveSellerContact,
  sellerTelegramUrl,
} from "@/lib/seller-contact";
import { cn } from "@/lib/utils";

type Props = {
  listing: Listing;
  className?: string;
  compact?: boolean;
};

function ContactRow({
  icon,
  label,
  href,
  external,
}: {
  icon: ReactNode;
  label: string;
  href?: string;
  external?: boolean;
}) {
  const content = (
    <>
      <span className="mt-0.5 shrink-0 text-muted">{icon}</span>
      <span className="min-w-0 break-words">{label}</span>
    </>
  );

  if (!href) {
    return <div className="flex items-start gap-2.5 text-[14px] text-ink">{content}</div>;
  }

  return (
    <a
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      className="flex items-start gap-2.5 text-[14px] font-medium text-emerald-dark transition-colors hover:text-emerald"
    >
      {content}
    </a>
  );
}

export function SellerContactBlock({ listing, className, compact = false }: Props) {
  if (!hasSellerContact(listing)) return null;

  const contact = resolveSellerContact(listing);
  if (!contact) return null;

  const sellerTypeLabel = listing.seller_type === "dealer" ? "Автосалон" : "Приват";

  return (
    <section
      className={cn(
        "rounded-2xl border border-border/80 bg-white",
        compact ? "p-4" : "p-5",
        className,
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-bold text-ink">Контакти продавця</h2>
        <span className="rounded-full bg-surface px-2.5 py-0.5 text-[11px] font-medium text-muted">
          {sellerTypeLabel}
        </span>
      </div>

      <div className="space-y-2.5">
        {contact.name && (
          <ContactRow icon={<IconUser size={16} />} label={contact.name} href={contact.url ?? undefined} external />
        )}

        {contact.phone && (
          <ContactRow
            icon={<Phone size={16} strokeWidth={1.6} />}
            label={formatPhoneDisplay(contact.phone)}
            href={`tel:${contact.phone}`}
          />
        )}

        {contact.telegram && (
          <ContactRow
            icon={<IconTelegram size={16} />}
            label={`@${contact.telegram.replace(/^@/, "")}`}
            href={sellerTelegramUrl(contact.telegram)}
            external
          />
        )}

        {!contact.name && contact.url && (
          <ContactRow
            icon={<IconUser size={16} />}
            label="Сторінка продавця"
            href={contact.url}
            external
          />
        )}
      </div>

      {listing.source === "auto_ria" && !contact.phone && (
        <p className="mt-3 text-[12px] leading-relaxed text-muted">
          Номер телефону AUTO.RIA не передає через API — відкрийте оголошення на джерелі.
        </p>
      )}
    </section>
  );
}
