"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ai as aiApi, type AiParseSearchResult } from "@/lib/api";

export type VoiceSearchPhase = "idle" | "listening" | "processing" | "done" | "error";

const SILENCE_MS = 5000;
const SILENCE_CHECK_INTERVAL_MS = 200;
const AUDIO_SILENCE_RMS = 0.018;

type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  onspeechstart?: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [index: number]: { transcript: string };
    };
  };
};

function getSpeechRecognition(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "audio/webm";
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "audio/webm";
}

export function useVoiceSearch() {
  const [phase, setPhase] = useState<VoiceSearchPhase>("idle");
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<AiParseSearchResult | null>(null);
  const [speechSupported, setSpeechSupported] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const stopRequestedRef = useRef(false);
  const finalTextRef = useRef("");
  const interimTextRef = useRef("");
  const lastSpeechAtRef = useRef(0);
  const silenceTimerRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioMonitorRef = useRef<number | null>(null);
  const stopRecordingRef = useRef<() => void>(() => {});

  useEffect(() => {
    setSpeechSupported(Boolean(getSpeechRecognition()));
  }, []);

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current != null) {
      window.clearInterval(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const clearAudioMonitor = useCallback(() => {
    if (audioMonitorRef.current != null) {
      window.cancelAnimationFrame(audioMonitorRef.current);
      audioMonitorRef.current = null;
    }
    if (audioContextRef.current) {
      void audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
  }, []);

  const bumpSpeechActivity = useCallback(() => {
    lastSpeechAtRef.current = Date.now();
  }, []);

  const cleanupMedia = useCallback(() => {
    clearAudioMonitor();
    mediaRecorderRef.current = null;
    if (mediaStreamRef.current) {
      for (const track of mediaStreamRef.current.getTracks()) track.stop();
      mediaStreamRef.current = null;
    }
    chunksRef.current = [];
  }, [clearAudioMonitor]);

  const cleanupRecognition = useCallback(() => {
    const rec = recognitionRef.current;
    recognitionRef.current = null;
    if (rec) {
      try {
        rec.abort();
      } catch {
        /* ignore */
      }
    }
  }, []);

  const reset = useCallback(() => {
    stopRequestedRef.current = false;
    finalTextRef.current = "";
    interimTextRef.current = "";
    clearSilenceTimer();
    cleanupRecognition();
    cleanupMedia();
    setPhase("idle");
    setTranscript("");
    setInterimTranscript("");
    setMessage(null);
    setResult(null);
  }, [cleanupMedia, cleanupRecognition, clearSilenceTimer]);

  const processText = useCallback(async (text: string) => {
    const query = text.trim();
    if (!query) {
      setPhase("error");
      setMessage("Не зрозумів — не почув запит. Спробуйте ще раз.");
      setResult(null);
      return;
    }

    setPhase("processing");
    setTranscript(query);
    setInterimTranscript("");

    try {
      const parsed = await aiApi.parseSearch(query);
      setTranscript(parsed.transcript || query);
      setMessage(parsed.message);
      setResult(parsed);

      if (!parsed.understood) {
        setPhase("error");
        return;
      }

      setPhase("done");
    } catch {
      setPhase("error");
      setMessage("Не вдалося обробити запит. Перевірте з'єднання та спробуйте ще раз.");
      setResult(null);
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (stopRequestedRef.current) return;
    stopRequestedRef.current = true;
    clearSilenceTimer();
    clearAudioMonitor();

    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.stop();
      } catch {
        const text = `${finalTextRef.current} ${interimTextRef.current}`.trim();
        void processText(text);
      }
      return;
    }

    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  }, [clearAudioMonitor, clearSilenceTimer, processText]);

  stopRecordingRef.current = () => {
    void stopRecording();
  };

  const startSilenceWatch = useCallback(() => {
    clearSilenceTimer();
    bumpSpeechActivity();
    silenceTimerRef.current = window.setInterval(() => {
      if (stopRequestedRef.current) return;
      if (Date.now() - lastSpeechAtRef.current >= SILENCE_MS) {
        stopRecordingRef.current();
      }
    }, SILENCE_CHECK_INTERVAL_MS);
  }, [bumpSpeechActivity, clearSilenceTimer]);

  const attachAudioSilenceMonitor = useCallback(
    (stream: MediaStream) => {
      clearAudioMonitor();
      if (typeof window === "undefined") return;

      const AudioCtx = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;

      const audioContext = new AudioCtx();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);

      const samples = new Uint8Array(analyser.fftSize);

      const tick = () => {
        if (stopRequestedRef.current) return;
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (let i = 0; i < samples.length; i += 1) {
          const normalized = (samples[i] - 128) / 128;
          sum += normalized * normalized;
        }
        const rms = Math.sqrt(sum / samples.length);
        if (rms >= AUDIO_SILENCE_RMS) {
          bumpSpeechActivity();
        }
        audioMonitorRef.current = window.requestAnimationFrame(tick);
      };

      audioMonitorRef.current = window.requestAnimationFrame(tick);
    },
    [bumpSpeechActivity, clearAudioMonitor],
  );

  const startWithSpeechRecognition = useCallback(() => {
    const Ctor = getSpeechRecognition();
    if (!Ctor) return false;

    const recognition = new Ctor();
    recognition.lang = "uk-UA";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = event => {
      bumpSpeechActivity();
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0]?.transcript ?? "";
        if (event.results[i].isFinal) {
          finalTextRef.current = `${finalTextRef.current} ${piece}`.trim();
        } else {
          interim = `${interim} ${piece}`.trim();
        }
      }
      interimTextRef.current = interim;
      setTranscript(finalTextRef.current);
      setInterimTranscript(interim);
    };

    recognition.onspeechstart = () => {
      bumpSpeechActivity();
    };

    recognition.onerror = event => {
      if (event.error === "aborted") return;
      clearSilenceTimer();
      setPhase("error");
      setMessage(
        event.error === "not-allowed"
          ? "Дозвольте доступ до мікрофона в налаштуваннях браузера."
          : "Не вдалося розпізнати мовлення. Спробуйте ще раз.",
      );
      cleanupRecognition();
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      clearSilenceTimer();
      if (!stopRequestedRef.current) return;
      const text = `${finalTextRef.current} ${interimTextRef.current}`.trim();
      void processText(text);
    };

    recognitionRef.current = recognition;
    stopRequestedRef.current = false;
    finalTextRef.current = "";
    interimTextRef.current = "";
    setPhase("listening");
    setTranscript("");
    setInterimTranscript("");
    setMessage(null);
    setResult(null);
    startSilenceWatch();

    try {
      recognition.start();
      return true;
    } catch {
      clearSilenceTimer();
      cleanupRecognition();
      return false;
    }
  }, [
    bumpSpeechActivity,
    cleanupRecognition,
    clearSilenceTimer,
    processText,
    startSilenceWatch,
  ]);

  const startWithMediaRecorder = useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setPhase("error");
      setMessage("Ваш браузер не підтримує запис голосу.");
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      attachAudioSilenceMonitor(stream);
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];

      recorder.ondataavailable = event => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        cleanupMedia();
        if (!stopRequestedRef.current) return;
        const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
        void (async () => {
          setPhase("processing");
          try {
            const parsed = await aiApi.transcribeSearch(blob);
            setTranscript(parsed.transcript || "");
            setMessage(parsed.message);
            setResult(parsed);
            if (!parsed.understood) {
              setPhase("error");
              return;
            }
            setPhase("done");
          } catch {
            setPhase("error");
            setMessage("Не вдалося розпізнати голос. Спробуйте ще раз.");
            setResult(null);
          }
        })();
      };

      mediaRecorderRef.current = recorder;
      stopRequestedRef.current = false;
      setPhase("listening");
      setTranscript("");
      setInterimTranscript("");
      setMessage("Говоріть… запис зупиниться після 5 сек тиші.");
      setResult(null);
      startSilenceWatch();
      recorder.start();
      return true;
    } catch {
      cleanupMedia();
      setPhase("error");
      setMessage("Дозвольте доступ до мікрофона в налаштуваннях браузера.");
      return false;
    }
  }, [attachAudioSilenceMonitor, cleanupMedia, startSilenceWatch]);

  const start = useCallback(async () => {
    cleanupRecognition();
    cleanupMedia();
    clearSilenceTimer();
    stopRequestedRef.current = false;
    finalTextRef.current = "";
    interimTextRef.current = "";
    setResult(null);

    const ok = startWithSpeechRecognition();
    if (ok) return;
    await startWithMediaRecorder();
  }, [cleanupMedia, cleanupRecognition, clearSilenceTimer, startWithMediaRecorder, startWithSpeechRecognition]);

  useEffect(() => {
    return () => {
      clearSilenceTimer();
      clearAudioMonitor();
    };
  }, [clearAudioMonitor, clearSilenceTimer]);

  const displayText =
    phase === "listening"
      ? `${transcript}${interimTranscript ? (transcript ? " " : "") + interimTranscript : ""}`.trim()
      : transcript;

  return {
    phase,
    transcript: displayText,
    message,
    result,
    speechSupported,
    start,
    stopRecording,
    reset,
    isActive: phase === "listening" || phase === "processing",
  };
}
