import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/legal/LegalPage";
import { OperatorRequisites } from "@/components/legal/OperatorRequisites";
import { LiqPayLogo } from "@/components/brand/LiqPayLogo";
import { PRICING_PLANS, SUPPORT_EMAIL } from "@/lib/pricing-plans";

export const metadata: Metadata = {
  title: "Оплата і повернення — Carbit",
  description:
    "Умови оплати, надання цифрової послуги та повернення коштів у сервісі Carbit. Оплата через LiqPay.",
};

const paidPlans = PRICING_PLANS.filter(p => p.id !== "free");

const sections = [
  {
    title: "1. Що ви купуєте",
    content: (
      <>
        <p>
          Carbit продає <strong className="text-ink">цифрову підписку</strong> на доступ до сервісу
          моніторингу оголошень авторинку України (веб-кабінет, пошуки, сповіщення).
          Фізичних товарів немає — доставка не потрібна.
        </p>
        <p className="mt-3">Повний перелік платних послуг і актуальні ціни:</p>
        <ul>
          {paidPlans.map(plan => (
            <li key={plan.id}>
              <strong className="text-ink">{plan.name}</strong> — {plan.price} грн / 30 днів.{" "}
              {plan.description}
            </li>
          ))}
        </ul>
        <p>
          Актуальні тарифи також на сторінці <Link href="/pricing">Тарифи</Link>. Пробний період
          «Безкоштовно» (7 днів) не є платною послугою.
        </p>
      </>
    ),
  },
  {
    title: "2. Оплата",
    content: (
      <>
        <p>Оплата здійснюється авансом за обраний період підписки (30 днів для платних тарифів).</p>
        <ul>
          <li>
            Онлайн: банківська картка Visa / Mastercard через платіжний сервіс{" "}
            <strong className="text-ink">LiqPay</strong> (ПриватБанк).
          </li>
          <li>
            Банківський переказ на рахунок ФОП за реквізитами нижче (у призначенні платежу вкажіть
            email акаунту та назву тарифу).
          </li>
        </ul>
        <div className="not-prose my-4 flex items-center gap-3 rounded-xl border border-border/60 bg-surface/50 px-4 py-3">
          <LiqPayLogo height={24} />
          <span className="text-[13px] text-muted">Безпечна оплата карткою через LiqPay</span>
        </div>
        <p>Реквізити продавця:</p>
        <OperatorRequisites />
      </>
    ),
  },
  {
    title: "3. Надання послуги (замість доставки)",
    content: (
      <>
        <p>
          Після підтвердження успішної оплати доступ до обраного тарифу активується в акаунті
          автоматично або службою підтримки протягом <strong className="text-ink">до 24 годин</strong>{" "}
          у робочий час.
        </p>
        <p>
          Послуга надається онлайн на сайті <strong className="text-ink">carbit.info</strong>.
          Фізична доставка відсутня.
        </p>
      </>
    ),
  },
  {
    title: "4. Повернення коштів",
    content: (
      <>
        <p>
          Ви можете відмовитись від підписки та вимагати повернення коштів відповідно до Закону
          України «Про захист прав споживачів» і цих правил:
        </p>
        <ul>
          <li>
            Якщо доступ до платної послуги <strong className="text-ink">ще не надано</strong> —
            повернення 100% оплати.
          </li>
          <li>
            Якщо послугу вже активовано — повернення можливе пропорційно до невикористаних днів
            періоду, якщо сервіс суттєво не працював з вини продавця.
          </li>
          <li>
            Заява на повернення: надішліть лист на{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a> з email акаунту, датою платежу та
            причиною. Розгляд — до 14 календарних днів.
          </li>
          <li>
            Кошти повертаються тим самим способом оплати (LiqPay / банківський переказ) у строки
            платіжної системи / банку.
          </li>
        </ul>
      </>
    ),
  },
  {
    title: "5. Контакти служби підтримки",
    content: (
      <>
        <ul>
          <li>
            Email: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
          </li>
          <li>
            Адреса продавця: 02055, м. Київ, вул. Урлівська, 20, кв. 79 (підконтрольна територія
            України)
          </li>
        </ul>
        <p>
          Детальні умови користування — у розділі <Link href="/terms">Умови використання</Link>.
          Повний юридичний текст — у <Link href="/oferta">Договорі публічної оферти</Link>.
        </p>
      </>
    ),
  },
];

export default function PaymentPage() {
  return (
    <LegalPage
      title="Оплата і повернення"
      subtitle="Правила оплати підписки Carbit, надання цифрової послуги та повернення коштів. Приймаємо оплату через LiqPay."
      updated="14 липня 2026"
      sections={sections}
    />
  );
}
