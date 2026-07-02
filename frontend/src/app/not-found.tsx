import Link from "next/link";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center bg-canvas px-4 py-12">
      <div className="w-full max-w-md text-center">
        <CarbitLogo variant="full" height={36} className="mx-auto mb-8" />

        <p className="text-[72px] font-bold leading-none tracking-tight text-ink/10 sm:text-[96px]">
          404
        </p>

        <h1 className="mt-2 text-xl font-semibold text-ink sm:text-2xl">
          Сторінку не знайдено
        </h1>

        <p className="mt-3 text-sm leading-relaxed text-muted sm:text-[15px]">
          Можливо, посилання застаріло або сторінку було переміщено. Перевірте адресу або
          поверніться на головну.
        </p>

        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link href="/">
            <Button size="lg">На головну</Button>
          </Link>
          <Link href="/app/dashboard">
            <Button variant="secondary" size="lg">
              У кабінет
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
