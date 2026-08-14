const VIDEO_SRC = "/video-instructions.mp4";

export function VideoInstructions() {
  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-border/60 bg-ink shadow-card aspect-video">
      <video
        src={VIDEO_SRC}
        className="absolute inset-0 h-full w-full object-cover"
        controls
        playsInline
        preload="metadata"
        title="Як шукати авто в Carbit — відеоінструкція"
        aria-label="Відеоінструкція: пошук і моніторинг авто оголошень у Carbit"
      >
        Ваш браузер не підтримує відтворення відео. Дивіться інструкцію після реєстрації в кабінеті
        Carbit.
      </video>
    </div>
  );
}
