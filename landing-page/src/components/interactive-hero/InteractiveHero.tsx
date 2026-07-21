"use client";

import React, {
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { StatusDot } from "../Logo";
import { Dropzone } from "./Dropzone";
import { VibeCheck } from "./VibeCheck";
import { Gate } from "./Gate";
import { ProcessingState } from "./ProcessingState";
import { Reveal } from "./Reveal";
import { type ComponentState, type ReplyItem, EASE_OUT } from "./types";
import { APP_URLS, API_URLS } from "@/app/constants";
import posthog from "posthog-js";

/* ───────────────────────────────────────────
   Interactive Lead Magnet Hero
   Orchestrates 5 states:
     idle → vibe_check → gate → processing → reveal
   ─────────────────────────────────────────── */

interface ApiResponse {
  status: "success" | "rate_limited" | "failed";
  cached?: boolean;
  replies?: ReplyItem[];
  detail?: string;
  retry_after_seconds?: number;
  app_url?: string;
}

interface InteractiveHeroProps {
  onRepliesReady?: (replies: ReplyItem[]) => void;
}

export function InteractiveHero({ onRepliesReady }: InteractiveHeroProps) {
  // ── State machine ──
  const [state, setState] = useState<ComponentState>("idle");

  // Collected data
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [selectedVibe, setSelectedVibe] = useState<string | null>(null);
  const [email, setEmail] = useState<string>("");

  // API state
  const [apiError, setApiError] = useState<string | null>(null);
  const [apiResponse, setApiResponse] = useState<ApiResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ── Handlers ──

  const onImageSelected = useCallback((file: File) => {
    setImageFile(file);
    // Convert file to base64 for API
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      // Strip data:image/...;base64, prefix
      const base64 = result.split(",")[1] || result;
      setImageBase64(base64);
    };
    reader.readAsDataURL(file);
    setState("vibe_check");
    posthog.capture("screenshot_uploaded", {
      file_type: file.type,
      file_size: file.size,
    });
  }, []);

  const onVibeSelect = useCallback((id: string) => {
    setSelectedVibe(id);
    setState("gate");
    posthog.capture("vibe_selected", { vibe: id });
  }, []);

  const onGateSubmit = useCallback(
    async (submittedEmail: string) => {
      if (!imageBase64 || !selectedVibe) return;

      setEmail(submittedEmail);
      setApiError(null);
      posthog.identify(submittedEmail);
      // Store distinct_id in sessionStorage for re-identification on return visits
      sessionStorage.setItem("posthog_distinct_id", submittedEmail);
      const emailDomain = submittedEmail.split("@")[1] || "unknown";
      posthog.capture("lead_email_submitted", {
        vibe: selectedVibe,
        email_domain: emailDomain,
      });

      // Move to processing state immediately — shows the real terminal animation
      setState("processing");

      // Abort previous request if any
      if (abortRef.current) {
        abortRef.current.abort();
      }
      const abortController = new AbortController();
      abortRef.current = abortController;

      try {
        const response = await fetch(API_URLS.leadMagnet, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image: imageBase64,
            direction: selectedVibe,
            email: submittedEmail,
          }),
          signal: abortController.signal,
        });

        const data: ApiResponse = await response.json();

        if (!response.ok) {
          // Handle 429, 502, 422 etc. — go back to gate with error
          setApiResponse(data);
          setApiError(data.detail || "Something went wrong.");
          if (data.status === "rate_limited") {
            posthog.capture("hero_rate_limited", {
              retry_after_seconds: data.retry_after_seconds,
            });
          }
          setState("gate");
          return;
        }

        // Success — pass replies up to page.tsx for the AppMockup
        setApiResponse(data);
        setState("reveal");
        posthog.capture("replies_revealed", {
          reply_count: data.replies?.length ?? 0,
          cached: data.cached ?? false,
          vibe: selectedVibe,
        });
        if (onRepliesReady && data.replies) {
          onRepliesReady(data.replies);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        setApiError("Network error. Please try again.");
        setState("gate");
      }
    },
    [imageBase64, selectedVibe]
  );

  const onReset = useCallback(() => {
    setState("idle");
    setImageFile(null);
    setImageBase64(null);
    setSelectedVibe(null);
    setEmail("");
    setApiError(null);
    setApiResponse(null);
  }, []);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  // ── Floating particles for background ──
  const floatingParticles = useMemo(
    () =>
      Array.from({ length: 12 }).map((_, i) => {
        const seed = (i * 0.618033988749895) % 1;
        const seed2 = (i * 0.3819660112501051) % 1;
        return {
          left: `${seed * 100}%`,
          top: `${seed2 * 100}%`,
          duration: 4 + seed * 4,
        };
      }),
    []
  );

  const isRateLimited =
    apiResponse?.status === "rate_limited" ||
    (state === "gate" && apiError?.toLowerCase().includes("rate limit"));

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-4 py-20 sm:py-28 overflow-hidden">
      {/* === Animated ambient glow === */}
      <motion.div
        className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full pointer-events-none z-0"
        style={{
          background:
            "radial-gradient(circle, rgba(255,0,60,0.08) 0%, transparent 70%)",
        }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 6,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* === Background gradient glow === */}
      <div className="pointer-events-none absolute inset-0 z-0">
        <div
          className="absolute left-1/2 top-1/3 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-[0.04]"
          style={{
            background: "radial-gradient(circle, #ff003c 0%, transparent 70%)",
          }}
        />
      </div>

      {/* === Grid pattern overlay === */}
      <div
        className="pointer-events-none absolute inset-0 z-0 opacity-[0.015]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* === Floating particles === */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        {floatingParticles.map((p, i) => (
          <motion.div
            key={i}
            className="absolute h-1 w-1 rounded-full bg-nothing-white/10"
            style={{ left: p.left, top: p.top }}
            animate={{ y: [0, -40, 0], opacity: [0, 0.3, 0] }}
            transition={{
              duration: p.duration,
              repeat: Infinity,
              delay: i * 0.6,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>

      {/* === Content === */}
      <div className="relative z-10 flex w-full max-w-3xl flex-col items-center">
        {/* Animated area */}
        <div className="w-full min-h-[550px] flex items-start justify-center">
          <AnimatePresence mode="wait">
            {state === "idle" && (
              <Dropzone key="idle" onImageSelected={onImageSelected} />
            )}

            {state === "vibe_check" && (
              <VibeCheck key="vibe_check" onSelect={onVibeSelect} />
            )}

            {state === "gate" && !isRateLimited && (
              <Gate key="gate" onSubmit={onGateSubmit} error={apiError} />
            )}

            {state === "processing" && <ProcessingState key="processing" />}

            {/* Show rate-limited state before reveal */}
            {state === "gate" && isRateLimited && (
              <Reveal
                key="rate_limited"
                replies={[]}
                isRateLimited={true}
                appUrl={apiResponse?.app_url || APP_URLS.googlePlay}
                onReset={onReset}
              />
            )}

            {state === "reveal" && (
              <Reveal
                key="reveal"
                replies={apiResponse?.replies || []}
                isCached={apiResponse?.cached || false}
                onReset={onReset}
              />
            )}
          </AnimatePresence>
        </div>

        {/* Bottom status bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 0.5 }}
          className="mt-12 flex items-center gap-3 rounded-full border border-nothing-border bg-nothing-surface/80 px-5 py-2 text-[10px] font-mono text-nothing-text-tertiary backdrop-blur-sm"
        >
          <StatusDot active />
          <span>
            STATUS:{" "}
            {state === "idle"
              ? "AWAITING_INPUT"
              : state === "vibe_check"
              ? "VIBE_SELECTION"
              : state === "processing"
              ? "GENERATING"
              : state === "gate"
              ? isRateLimited
                ? "RATE_LIMITED"
                : "AWAITING_EMAIL"
              : "COMPLETE"}
          </span>
          <span className="text-nothing-text-tertiary/50">&bull;</span>
          <span>
            {state === "idle"
              ? "DROP / PASTE SCREENSHOT"
              : state === "vibe_check"
              ? `IMAGE_LOCKED (${imageFile?.name ?? "screenshot.png"})`
              : state === "processing"
              ? "AI_GENERATION_IN_PROGRESS"
              : state === "gate"
              ? isRateLimited
                ? "TRY THE APP"
                : "EMAIL_REQUIRED"
              : "SESSION_ACTIVE"}
          </span>
        </motion.div>
      </div>

      {/* Bottom gradient fade */}
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-10 h-32 bg-gradient-to-t from-nothing-black to-transparent" />
    </section>
  );
}
