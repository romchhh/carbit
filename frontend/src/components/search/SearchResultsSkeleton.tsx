"use client";

type Props = {
  count?: number;
};

export function SearchResultsSkeleton({ count = 4 }: Props) {
  return (
    <div className="space-y-3" aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="overflow-hidden rounded-2xl border border-border/70 bg-white"
        >
          <div className="flex flex-col sm:flex-row">
            <div className="h-[180px] w-full shrink-0 animate-pulse bg-surface sm:h-[148px] sm:w-[220px]" />
            <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
              <div className="h-4 w-2/3 animate-pulse rounded bg-surface" />
              <div className="h-6 w-1/3 animate-pulse rounded bg-surface" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-surface" />
              <div className="mt-auto h-3 w-1/4 animate-pulse rounded bg-surface" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
