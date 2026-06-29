/** YouTube embed або прямий URL відео — заповнити після зйомки інструкції */
const VIDEO_EMBED_URL = "";

export function VideoInstructions() {
  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-border/60 bg-ink shadow-card aspect-video">
      {VIDEO_EMBED_URL ? (
        <iframe
          src={VIDEO_EMBED_URL}
          title="Відеоінструкція Carbit"
          className="absolute inset-0 h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-ink via-ink-2 to-ink px-6 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/20">
            <svg
              viewBox="0 0 24 24"
              fill="currentColor"
              className="ml-1 h-7 w-7 text-white"
              aria-hidden
            >
              <path d="M8 5.14v13.72L19 12 8 5.14z" />
            </svg>
          </div>
          <div>
            <p className="text-[17px] font-semibold text-white">Відеоінструкція</p>
            <p className="mt-1.5 max-w-[260px] text-[13px] leading-snug text-white/55">
              Скоро тут буде покроковий огляд сервісу
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
