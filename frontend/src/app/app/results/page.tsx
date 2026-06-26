"use client";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { IconArrowRight, IconHeart, IconFilter } from "@/components/icons";
import { ExportMenu } from "@/components/search/ExportMenu";
import { cn } from "@/lib/utils";
import type { ExportListing } from "@/lib/export-listings";

type ResultListing = ExportListing & {
  id: string;
  risk: string;
  priceDown?: boolean;
  oldPrice?: number;
};

const listings: ResultListing[] = [
  { id:"1", title:"Toyota Camry 2.5 AT", year:2021, mileage:45000, price:780000, region:"Київ", src:"AUTO.RIA", time:"12 хв", risk:"low",  priceDown:true,  oldPrice:810000 },
  { id:"2", title:"Toyota Camry 2.0 AT", year:2019, mileage:88000, price:610000, region:"Київ", src:"Telegram",time:"34 хв", risk:"medium",priceDown:false, oldPrice:0      },
  { id:"3", title:"Toyota Camry 3.5 AT", year:2022, mileage:31000, price:890000, region:"Харків",src:"OLX",   time:"1 год", risk:"low",  priceDown:false, oldPrice:0      },
  { id:"4", title:"Toyota Camry 2.5 AT", year:2020, mileage:62000, price:720000, region:"Одеса", src:"AUTO.RIA",time:"3 год",risk:"medium",priceDown:true, oldPrice:760000 },
  { id:"5", title:"Toyota Camry 2.0 AT", year:2021, mileage:51000, price:690000, region:"Дніпро",src:"OLX",   time:"5 год",risk:"high",  priceDown:false, oldPrice:0      },
];
const riskMeta: Record<string,{label:string;cn:string}> = {
  low:    { label:"Брати",       cn:"text-emerald-dark bg-emerald-light" },
  medium: { label:"Торгуватись", cn:"text-yellow-700 bg-yellow-50" },
  high:   { label:"Пропустити",  cn:"text-red-600 bg-red-50" },
};

export default function ResultsPage() {
  return (
    <div className="max-w-[860px]">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-[12px] text-muted mb-6">
              <Link href="/app/dashboard" className="hover:text-ink">Мої пошуки</Link>
              <span>/</span>
              <span className="text-ink font-medium">Toyota Camry під перепродаж</span>
            </div>

            {/* Toolbar */}
            <div className="bg-white border border-border rounded-xl px-5 py-3.5 flex items-center justify-between mb-5">
              <div className="flex items-center gap-4 text-[13px]">
                <span className="flex items-center gap-2 text-emerald-dark font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald animate-pulse"/>Активний
                </span>
                <span className="text-muted">·</span>
                <span className="text-muted">Знайдено <strong className="text-ink">{listings.length}</strong></span>
                <span className="text-muted">·</span>
                <span className="text-emerald-dark font-semibold">12 нових</span>
              </div>
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-1.5 text-[12px] text-muted hover:text-ink transition-colors">
                  <IconFilter size={12}/> Фільтри
                </button>
                <ExportMenu items={listings} filename="toyota-camry" iconSize={12} />
                <select className="text-[12px] bg-white border border-border rounded-lg px-3 py-1.5 text-muted focus:outline-none">
                  <option>Спочатку дешеві</option>
                  <option>Спочатку нові</option>
                </select>
              </div>
            </div>

            {/* Cards */}
            <div className="space-y-3">
              {listings.map(r => {
                const risk = riskMeta[r.risk];
                return (
                  <article key={r.id} className="bg-white border border-border rounded-xl p-5 flex gap-4 hover:border-ink/15 transition-colors">
                    <div className="w-44 h-28 bg-surface rounded-lg shrink-0 overflow-hidden flex items-center justify-center">
                      <svg width="32" height="32" viewBox="0 0 28 28" fill="none" className="opacity-10">
                        <rect x="12.5" y="0" width="3" height="28" fill="#0A0C0E"/>
                        <rect x="0" y="12.5" width="28" height="3" fill="#0A0C0E"/>
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-[15px] font-bold text-ink">{r.title}</h3>
                          <p className="text-[12px] text-muted mt-0.5">{r.year} · {r.mileage.toLocaleString("uk-UA")} км · {r.region}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-[20px] font-black text-ink leading-none">{r.price.toLocaleString("uk-UA")} <span className="text-[13px] text-muted font-medium">грн</span></div>
                          {r.priceDown && r.oldPrice != null && (
                            <div className="text-[11px] text-red-500 line-through">{r.oldPrice.toLocaleString("uk-UA")}</div>
                          )}
                        </div>
                      </div>
                      <div className="mt-3 flex items-center gap-2.5 flex-wrap">
                        <span className={cn("text-[11px] font-bold px-2 py-0.5 rounded", risk.cn)}>{risk.label}</span>
                        <Badge variant="outline">{r.src}</Badge>
                        {r.priceDown && <Badge variant="red">↓ Ціна знижена</Badge>}
                        <span className="text-[11px] text-muted">{r.time} тому</span>
                        <div className="ml-auto flex items-center gap-2">
                          <button className="w-7 h-7 rounded-lg border border-border flex items-center justify-center text-muted hover:text-ink transition-colors">
                            <IconHeart size={12}/>
                          </button>
                          <Link href={`/app/listing/${r.id}`}
                            className="text-[12px] font-semibold text-emerald-dark flex items-center gap-1 hover:underline">
                            Деталі <IconArrowRight size={11}/>
                          </Link>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>

            <button className="mt-6 w-full py-3 border border-border rounded-xl text-[13px] text-muted hover:text-ink hover:border-ink/20 transition-colors">
              Показати більше результатів
            </button>
    </div>
  );
}
