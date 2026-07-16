import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  random,
} from "remotion";
import { loadFont as loadHeading } from "@remotion/google-fonts/SpaceGrotesk";
import { loadFont as loadBody } from "@remotion/google-fonts/DMSans";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { CookdShortProps } from "./types";
import { generateHook } from "./hookGenerator";

// ── Fonts — matches landing-page globals.css tokens exactly:
// --font-heading: Space Grotesk, --font-sans: DM Sans, --font-mono: mono stack.
const { fontFamily: headingFont } = loadHeading("normal", {
  weights: ["500", "600", "700"],
});
const { fontFamily: bodyFont } = loadBody("normal", {
  weights: ["400", "500", "700"],
});
const { fontFamily: monoFont } = loadMono("normal", {
  weights: ["500", "600"],
});

// ── Brand tokens — lifted from landing-page/src/app/globals.css and
// RizzBotV2 ui/theme/Color.kt: pitch black, pure white, exactly one accent
// (brand-primary / neon-red, #E11D48) reserved for the primary action.
const COOKD_THEME = {
  nothingBlack: "#000000",
  nothingWhite: "#FFFFFF",
  neonRed: "#E11D48",
  nothingSurface: "#0A0A0A",
  nothingBorder: "rgba(255, 255, 255, 0.1)",
  textSecondary: "rgba(255, 255, 255, 0.45)",
  successGreen: "#00FF66",
};

const SCRAMBLE_CHARS = "!<>-_\\/[]{}—=+*^?#_";

// ── Safe zones for platform UI overlays ──
// Instagram Reels: username/caption/audio-disc sit in the bottom ~340px, and
// like/comment/share/save icons run down the right edge in a ~150px column.
// YouTube Shorts: subscribe pill (bottom-left) + description affordance push
// the bottom dead zone to ~360px, with a similar right-edge icon rail.
// These margins keep content inside the ~900x1400 area that's clear on both.
const SAFE_TOP = 190;
const SAFE_BOTTOM = 340;
const SAFE_LEFT = 60;
const SAFE_RIGHT = 160;

function seedFrom(...parts: string[]): number {
  let h = 0;
  const s = parts.join("|");
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function pick<T>(arr: readonly T[], seed: number, offset = 0): T {
  return arr[(seed + offset) % arr.length];
}

// Pitch-black, single-accent backgrounds — no off-brand hues. Variety comes
// only from the vignette position, matching "strict dark mode, no compromises".
const BG_VARIANTS = [
  "radial-gradient(ellipse at 50% 0%, #0a0a0a 0%, #000000 100%)",
  "radial-gradient(ellipse at 15% 10%, #0a0a0a 0%, #000000 70%)",
  "radial-gradient(ellipse at 85% 10%, #0a0a0a 0%, #000000 70%)",
  "radial-gradient(ellipse at 50% 100%, #0a0a0a 0%, #000000 85%)",
];

const THINKING_LABELS = [
  "COOKD IS COOKING",
  "READING THE VIBE",
  "ANALYZING THE CHAT",
  "COMPOSING YOUR MOVE",
];

const REVEAL_LABELS = [
  "THE WINNING LINE",
  "YOUR REPLY",
  "THE MOVE",
  "PLAY THIS",
];

const THINKING_LINES = [
  ["reading context…", "analyzing her tone…", "crafting frame…"],
  ["decoding signals…", "scanning for hooks…", "building bait…"],
  ["reviewing strategy…", "optimizing for reply…", "calculating timing…"],
];

// ── Icons (hand-inlined, heroicons-style outline paths — no emoji) ──

const CameraIcon: React.FC<{ size?: number; color?: string }> = ({
  size = 24,
  color = "currentColor",
}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      stroke={color}
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z"
    />
  </svg>
);

const SparkleIcon: React.FC<{ size?: number; color?: string }> = ({
  size = 20,
  color = "currentColor",
}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      fill={color}
      d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
    />
  </svg>
);

// ── Brand logo watermark (inline SVG — matches public/logo.svg exactly) ──

const LogoWatermark: React.FC = () => (
  <div
    style={{
      position: "absolute",
      top: 56,
      left: SAFE_LEFT,
      zIndex: 400,
      display: "flex",
      alignItems: "center",
      gap: "12px",
      pointerEvents: "none",
      filter: "drop-shadow(0 2px 10px rgba(0,0,0,0.6))",
    }}
  >
    <svg width="40" height="40" viewBox="0 0 108 108" fill="none">
      <circle cx="54" cy="54" r="28" fill="#FFFFFF" />
      <path
        fill="#000000"
        fillRule="evenodd"
        d="M63.73,45.51 A12,12 0 1,0 63.73,62.49 L61.31,60.07 A8.6,8.6 0 1,1 61.31,47.93 Z"
      />
    </svg>
    <span
      style={{
        fontFamily: monoFont,
        fontSize: "22px",
        fontWeight: 600,
        color: "rgba(255,255,255,0.92)",
        letterSpacing: "1px",
      }}
    >
      COOKD
    </span>
  </div>
);

// ── Neutral contact avatar chip (no rainbow palette — one accent only,
// reserved for the "you" side; everyone else gets the same neutral chip) ──

const Avatar: React.FC<{
  size: number;
  initial: string;
  variant: "contact" | "you";
  fontSize: number;
}> = ({ size, initial, variant, fontSize }) => (
  <div
    style={{
      width: `${size}px`,
      height: `${size}px`,
      borderRadius: "50%",
      backgroundColor:
        variant === "you" ? COOKD_THEME.neonRed : COOKD_THEME.nothingSurface,
      border: `1.5px solid ${
        variant === "you" ? "rgba(225, 29, 72, 0.4)" : COOKD_THEME.nothingBorder
      }`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: headingFont,
      fontSize: `${fontSize}px`,
      fontWeight: 700,
      flexShrink: 0,
      color: COOKD_THEME.nothingWhite,
    }}
  >
    {initial}
  </div>
);

// ── Typing dots ──

const TypingDots: React.FC<{ frame: number; fps: number }> = ({
  frame,
  fps,
}) => (
  <div
    style={{
      display: "flex",
      gap: "8px",
      padding: "16px 20px",
    }}
  >
    {[0, 1, 2].map((i) => {
      const dotSpring = spring({
        frame: frame - i * 3,
        fps,
        config: { damping: 20, stiffness: 300, mass: 0.5 },
      });
      return (
        <div
          key={i}
          style={{
            width: "12px",
            height: "12px",
            borderRadius: "50%",
            backgroundColor: COOKD_THEME.textSecondary,
            opacity: interpolate(dotSpring, [0, 1], [0.2, 0.8]),
            transform: `scale(${dotSpring})`,
          }}
        />
      );
    })}
  </div>
);

// ── Main composition ──

export const CookdChatShortVideo: React.FC<CookdShortProps> = ({
  personName,
  messages,
  winningLine,
  strategyLabel,
  voiceoverAudio,
  hookStyle,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const hookText = generateHook({
    hookStyle,
    personName,
    messages,
    winningLine,
    strategyLabel,
  });

  const hookWords: { text: string; emph: boolean }[] = [];
  hookText.split('"').forEach((segment, segIndex) => {
    const emph = segIndex % 2 === 1;
    const words = segment.split(/\s+/).filter((w) => w.length > 0);
    words.forEach((word, wi) => {
      let text = word;
      if (emph && wi === 0) text = `"${text}`;
      if (emph && wi === words.length - 1) text = `${text}"`;
      hookWords.push({ text, emph });
    });
  });

  const seed = seedFrom(personName + strategyLabel);
  const bgGradient = pick(BG_VARIANTS, seed);
  const thinkingLabel = pick(THINKING_LABELS, seed, 1);
  const revealLabel = pick(REVEAL_LABELS, seed, 2);
  const thinkingLines = pick(THINKING_LINES, seed, 3);

  const MSG_PACE = 28;
  const chatStartFrame = 65;
  const analyzeStartFrame = chatStartFrame + messages.length * MSG_PACE;
  const ANALYZE_FRAMES = 18;
  const revealStartFrame = analyzeStartFrame + ANALYZE_FRAMES;
  const typingSpeed = 2;
  const typingDuration = winningLine.length * typingSpeed;
  const OUTRO_HOLD = 120;
  const outroStartFrame = revealStartFrame + typingDuration + 75;
  const totalDuration = outroStartFrame + OUTRO_HOLD;

  // Matches globals.css `.animate-neon-pulse` keyframe (3s ease-in-out loop),
  // the one place the design system allows a glow instead of a hard border.
  const pulseT = (Math.sin((frame / 90) * Math.PI * 2) + 1) / 2;
  const pulseBlur = interpolate(pulseT, [0, 1], [20, 30]);
  const pulseSpread = interpolate(pulseT, [0, 1], [40, 60]);
  const pulseAlpha1 = interpolate(pulseT, [0, 1], [0.15, 0.25]);
  const pulseAlpha2 = interpolate(pulseT, [0, 1], [0.05, 0.1]);

  // Once the AI reveals its line, the earlier back-and-forth dims down so
  // the payoff is the one bright thing on screen — a focus-pull, not just
  // another element at the same brightness as everything before it.
  const focusDim =
    frame >= revealStartFrame
      ? interpolate(frame, [revealStartFrame, revealStartFrame + 15], [1, 0.32], {
          extrapolateRight: "clamp",
        })
      : 1;

  return (
    <AbsoluteFill
      style={{
        fontFamily: bodyFont,
        color: COOKD_THEME.nothingWhite,
      }}
    >
      {voiceoverAudio && <Audio src={voiceoverAudio} volume={0.8} />}

      {/* Background lives on its own layer with a slow "breathing" zoom —
          a static gradient reads as a dead screenshot no matter how much
          the foreground animates; this keeps something always moving. */}
      <AbsoluteFill
        style={{
          background: bgGradient,
          transform: `scale(${interpolate(
            Math.sin((frame / (totalDuration * 1.1)) * Math.PI),
            [0, 1],
            [1, 1.08]
          )})`,
        }}
      />

      {/* --- Persistent logo watermark (all frames) --- */}
      <LogoWatermark />

      {/* Progress bar — a filling bar is a well-worn "don't swipe away yet,
          there's a payoff coming" retention cue, and it also gives the
          frame continuous motion for its entire runtime. */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: SAFE_LEFT,
          right: SAFE_RIGHT,
          height: "3px",
          borderRadius: "2px",
          backgroundColor: "rgba(255,255,255,0.12)",
          zIndex: 400,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${interpolate(frame, [0, totalDuration], [0, 100], {
              extrapolateRight: "clamp",
            })}%`,
            backgroundColor: COOKD_THEME.neonRed,
          }}
        />
      </div>

      {/* Opening stinger — a standalone layer (not nested in the hook's own
          fade-in) so it actually hits full-opacity red at frame 0 instead of
          being multiplied down to a dark maroon wash by the parent's fade. */}
      {frame < 4 && (
        <AbsoluteFill
          style={{
            backgroundColor: COOKD_THEME.neonRed,
            opacity: interpolate(frame, [0, 1, 4], [1, 0.7, 0]),
            zIndex: 380,
            pointerEvents: "none",
          }}
        />
      )}

      {/* HOOK FRAME (first ~2 seconds) */}
      {frame < 60 && (
        <AbsoluteFill
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 200,
            opacity: interpolate(frame, [0, 5, 50, 60], [0, 1, 1, 0]),
            transform: `scale(${interpolate(
              frame,
              [0, 50, 60],
              [1, 1.05, 1.14]
            )})`,
            paddingLeft: SAFE_LEFT,
            paddingRight: SAFE_RIGHT,
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "36px",
              maxWidth: "90%",
            }}
          >
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "center",
                alignItems: "baseline",
                maxWidth: "100%",
                columnGap: "18px",
                rowGap: "6px",
                fontFamily: headingFont,
              }}
            >
              {hookWords.map((word, i) => {
                // Punchy, slightly underdamped spring — overshoots past 1 before
                // settling, so words "land" with a snap instead of easing in.
                // Capped (Math.min) so the overshoot can't grow large enough to
                // visually collide with the tightly-packed word next to it.
                const wordSpring = spring({
                  frame: frame - i * 1.6,
                  fps,
                  config: { damping: 9, stiffness: 240, mass: 0.6 },
                });
                const wordScale = Math.min(wordSpring, 1.08);
                // Per-word rotation jitter so the line lands like a chaotic
                // gang of pop-ins rather than one uniform wave — breaks the
                // monotone easing that makes smooth motion feel "quiet".
                const wordSeed = seedFrom(word.text, String(i));
                const rot = ((wordSeed % 5) - 2) * 2.2;
                return (
                  <span
                    key={i}
                    style={{
                      display: "inline-block",
                      fontSize: "72px",
                      fontWeight: 700,
                      lineHeight: 1.05,
                      letterSpacing: "-2px",
                      color: word.emph
                        ? COOKD_THEME.neonRed
                        : COOKD_THEME.nothingWhite,
                      opacity: interpolate(wordSpring, [0, 0.7], [0, 1], {
                        extrapolateRight: "clamp",
                      }),
                      transform: `translateY(${interpolate(
                        wordSpring,
                        [0, 1],
                        [28, 0]
                      )}px) scale(${wordScale}) rotate(${interpolate(
                        wordSpring,
                        [0, 1],
                        [rot, 0],
                        { extrapolateRight: "clamp" }
                      )}deg)`,
                    }}
                  >
                    {word.text}
                  </span>
                );
              })}
            </div>
            <div
              style={{
                width: `${interpolate(
                  spring({
                    frame: frame - hookWords.length * 1.6,
                    fps,
                    config: { damping: 14, stiffness: 160 },
                  }),
                  [0, 1],
                  [0, 160]
                )}px`,
                height: "3px",
                background: COOKD_THEME.neonRed,
                borderRadius: "2px",
              }}
            />
          </div>
        </AbsoluteFill>
      )}

      {/* --- CHAT UI (full bleed, no phone frame) --- */}
      {frame >= 55 && (
        <div
          style={{
            position: "absolute",
            top: SAFE_TOP,
            left: SAFE_LEFT,
            right: SAFE_RIGHT,
            bottom: SAFE_BOTTOM,
            display: "flex",
            flexDirection: "column",
            opacity: interpolate(frame, [55, 65], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            transform: `translateY(${interpolate(frame, [55, 70], [40, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })}px)`,
          }}
        >
          {/* Chat header */}
          <div
            style={{
              display: "flex",
              flexShrink: 0,
              justifyContent: "space-between",
              alignItems: "center",
              padding: "20px 0",
              borderBottom: `1px solid ${COOKD_THEME.nothingBorder}`,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
              }}
            >
              <Avatar
                size={48}
                initial={personName.charAt(0).toUpperCase()}
                variant="contact"
                fontSize={22}
              />
              <div
                style={{ display: "flex", flexDirection: "column", gap: "2px" }}
              >
                <span
                  style={{
                    fontFamily: headingFont,
                    fontSize: "24px",
                    fontWeight: 700,
                  }}
                >
                  {personName}
                </span>
                <span
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontFamily: monoFont,
                    fontSize: "15px",
                    fontWeight: 500,
                    letterSpacing: "0.5px",
                    color: COOKD_THEME.successGreen,
                  }}
                >
                  <span
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      backgroundColor: COOKD_THEME.successGreen,
                    }}
                  />
                  online
                </span>
              </div>
            </div>
            <CameraIcon size={26} color={COOKD_THEME.textSecondary} />
          </div>

          {/* Messages body — centered in the safe area so the thread never
              hugs the bottom edge where platform UI (likes/caption/audio)
              lives, and fills the dead space above it instead. */}
          <div
            style={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              paddingTop: "32px",
              paddingBottom: "16px",
              overflow: "hidden",
            }}
          >
            {/* Dims once the AI reveals its line — a focus-pull that makes
                the payoff the one bright thing on screen instead of just
                another element at the same brightness as the small talk. */}
            <div style={{ opacity: focusDim }}>
            {messages.map((msg, index) => {
              const entryFrame = chatStartFrame + index * MSG_PACE;
              const isThem = msg.sender === "them";
              const DOTS_WINDOW = 10;
              const showTypingDots =
                frame >= entryFrame - DOTS_WINDOW && frame < entryFrame;

              if (frame < entryFrame - DOTS_WINDOW) return null;

              return (
                <React.Fragment key={index}>
                  {showTypingDots && (
                    <div
                      style={{
                        display: "flex",
                        justifyContent: isThem ? "flex-start" : "flex-end",
                        marginBottom: "8px",
                      }}
                    >
                      {isThem && (
                        <div style={{ marginRight: "10px" }}>
                          <Avatar
                            size={36}
                            initial={personName.charAt(0).toUpperCase()}
                            variant="contact"
                            fontSize={16}
                          />
                        </div>
                      )}
                      <TypingDots
                        frame={frame - (entryFrame - DOTS_WINDOW)}
                        fps={fps}
                      />
                      {!isThem && (
                        <div style={{ marginLeft: "10px" }}>
                          <Avatar size={36} initial="Y" variant="you" fontSize={16} />
                        </div>
                      )}
                    </div>
                  )}

                  {frame >= entryFrame &&
                    (() => {
                      const reveal = interpolate(
                        frame - entryFrame,
                        [0, 10],
                        [0, 1],
                        {
                          extrapolateRight: "clamp",
                          easing: Easing.out(Easing.cubic),
                        }
                      );

                      return (
                        <div
                          style={{
                            maxHeight: `${interpolate(
                              reveal,
                              [0, 1],
                              [0, 500]
                            )}px`,
                            overflow: "hidden",
                            marginBottom: "16px",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "flex-end",
                              gap: "10px",
                              justifyContent: isThem
                                ? "flex-start"
                                : "flex-end",
                              transform: `translateY(${interpolate(
                                reveal,
                                [0, 1],
                                [30, 0]
                              )}px)`,
                              opacity: interpolate(reveal, [0, 0.6], [0, 1]),
                            }}
                          >
                            {isThem && (
                              <Avatar
                                size={36}
                                initial={personName.charAt(0).toUpperCase()}
                                variant="contact"
                                fontSize={16}
                              />
                            )}

                            <div
                              style={{
                                maxWidth: "78%",
                                padding: "18px 24px",
                                fontFamily: bodyFont,
                                fontSize: "24px",
                                lineHeight: 1.4,
                                backgroundColor: isThem
                                  ? COOKD_THEME.nothingSurface
                                  : "rgba(225, 29, 72, 0.08)",
                                border: `1px solid ${
                                  isThem
                                    ? COOKD_THEME.nothingBorder
                                    : "rgba(225, 29, 72, 0.2)"
                                }`,
                                color: COOKD_THEME.nothingWhite,
                                borderRadius: isThem
                                  ? "4px 12px 12px 12px"
                                  : "12px 4px 12px 12px",
                                fontWeight: 600,
                              }}
                            >
                              {msg.text}
                            </div>

                            {!isThem && (
                              <Avatar size={36} initial="Y" variant="you" fontSize={16} />
                            )}
                          </div>
                        </div>
                      );
                    })()}
                </React.Fragment>
              );
            })}
            </div>

            {/* AI Generation block */}
            {(() => {
              if (frame < analyzeStartFrame) return null;

              const isAnalyzing = frame < revealStartFrame;
              const charsToShow = Math.max(
                0,
                Math.floor((frame - revealStartFrame) / typingSpeed)
              );
              const visibleText = winningLine.substring(0, charsToShow);
              const isTyping = charsToShow < winningLine.length && !isAnalyzing;
              const randomScrambleChar = isTyping
                ? SCRAMBLE_CHARS[
                    Math.floor(random(frame) * SCRAMBLE_CHARS.length)
                  ]
                : "";
              const calcProgress = Math.min(
                99,
                Math.floor(((frame - analyzeStartFrame) / ANALYZE_FRAMES) * 100)
              );

              const aiReveal = interpolate(
                frame - analyzeStartFrame,
                [0, 10],
                [0, 1],
                {
                  extrapolateRight: "clamp",
                  easing: Easing.out(Easing.cubic),
                }
              );

              // The card "thunks" in with an overshoot pop right when the
              // analyzing→revealed cut happens — punchier than another fade.
              // Capped so the overshoot can't push the card into the message
              // bubble above it or outside its clipped container.
              const revealPunch = isAnalyzing
                ? 1
                : Math.min(
                    spring({
                      frame: Math.max(0, frame - revealStartFrame),
                      fps,
                      config: { damping: 9, stiffness: 260, mass: 0.6 },
                    }),
                    1.05
                  );

              // The line "lands" with a scale-snap + white flash the instant
              // typing finishes — the actual payoff moment, so it should feel
              // like an event, not just the cursor stopping.
              const finishFrame = revealStartFrame + typingDuration;
              const landedPunch =
                frame < finishFrame
                  ? 1
                  : Math.min(
                      spring({
                        frame: frame - finishFrame,
                        fps,
                        config: { damping: 8, stiffness: 300, mass: 0.5 },
                      }),
                      1.06
                    );
              const landedFlash = interpolate(
                frame,
                [finishFrame, finishFrame + 2, finishFrame + 12],
                [0, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );

              // A tiny high-frequency jitter while analyzing — reads as
              // "buzzing with anticipation" instead of sitting inert.
              const jitterX = isAnalyzing ? Math.sin(frame * 2.2) * 1.5 : 0;

              return (
                <div
                  style={{
                    maxHeight: `${interpolate(aiReveal, [0, 1], [0, 800])}px`,
                    overflow: "hidden",
                    marginTop: "8px",
                    transform: `translateY(${interpolate(
                      aiReveal,
                      [0, 1],
                      [30, 0]
                    )}px)`,
                    opacity: interpolate(aiReveal, [0, 0.6], [0, 1]),
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      width: "100%",
                      gap: "16px",
                      background: COOKD_THEME.nothingSurface,
                      padding: "24px 28px",
                      border: `1px solid ${
                        isAnalyzing
                          ? COOKD_THEME.textSecondary
                          : COOKD_THEME.neonRed
                      }`,
                      boxShadow: isAnalyzing
                        ? "none"
                        : `0 0 ${pulseBlur}px rgba(225, 29, 72, ${pulseAlpha1}), 0 0 ${pulseSpread}px rgba(225, 29, 72, ${pulseAlpha2})`,
                      borderRadius: "12px",
                      transform: `scale(${revealPunch}) translateX(${jitterX}px)`,
                    }}
                  >
                    {/* Header */}
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        borderBottom: `1px solid ${COOKD_THEME.nothingBorder}`,
                        paddingBottom: "12px",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: monoFont,
                          fontSize: "18px",
                          color: isAnalyzing
                            ? COOKD_THEME.textSecondary
                            : COOKD_THEME.neonRed,
                          fontWeight: 600,
                          letterSpacing: "1px",
                        }}
                      >
                        {isAnalyzing ? thinkingLabel : revealLabel}
                      </span>
                      {!isAnalyzing && (
                        <span
                          style={{
                            fontFamily: monoFont,
                            fontSize: "13px",
                            color: COOKD_THEME.nothingBlack,
                            backgroundColor: COOKD_THEME.successGreen,
                            padding: "4px 10px",
                            fontWeight: 600,
                            letterSpacing: "0.5px",
                            borderRadius: "4px",
                          }}
                        >
                          {strategyLabel}
                        </span>
                      )}
                    </div>

                    {/* Body */}
                    {isAnalyzing ? (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "16px",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "32px",
                          }}
                        >
                          {[0, 1, 2].map((i) => {
                            const pulse = spring({
                              frame: frame - i * 3,
                              fps,
                              config: { damping: 20, mass: 0.8 },
                            });
                            return (
                              <div
                                key={i}
                                style={{
                                  width: `${20 + i * 14}px`,
                                  height: `${20 + i * 14}px`,
                                  borderRadius: "50%",
                                  border: `2px solid ${COOKD_THEME.neonRed}`,
                                  opacity: interpolate(
                                    pulse,
                                    [0, 1],
                                    [0.1, 0.6 - i * 0.15]
                                  ),
                                  transform: `scale(${interpolate(
                                    pulse,
                                    [0, 1],
                                    [0.8, 1.2]
                                  )})`,
                                }}
                              />
                            );
                          })}
                        </div>
                        <div
                          style={{
                            fontFamily: monoFont,
                            color: COOKD_THEME.textSecondary,
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                            fontSize: "16px",
                            fontWeight: 500,
                            letterSpacing: "0.3px",
                          }}
                        >
                          <div>{thinkingLines[0]}</div>
                          <div>{thinkingLines[1]}</div>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                            }}
                          >
                            <span>Confidence</span>
                            <span
                              style={{
                                color: COOKD_THEME.successGreen,
                                fontWeight: 700,
                              }}
                            >
                              {calcProgress}%
                            </span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          gap: "12px",
                          alignItems: "flex-start",
                        }}
                      >
                        <div
                          style={{
                            width: "40px",
                            height: "40px",
                            borderRadius: "50%",
                            backgroundColor: "rgba(0, 255, 102, 0.12)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                            marginTop: "4px",
                          }}
                        >
                          <SparkleIcon size={20} color={COOKD_THEME.successGreen} />
                        </div>
                        <div style={{ flex: 1, position: "relative" }}>
                          <div
                            style={{
                              fontFamily: bodyFont,
                              fontSize: "30px",
                              fontWeight: 600,
                              lineHeight: 1.4,
                              visibility: "hidden",
                            }}
                            aria-hidden
                          >
                            {/* Trailing glyph matches the cursor block so this
                                reservation div wraps identically to the visible
                                text below — otherwise a 1-word wrap mismatch
                                lets the last word spill outside the card. */}
                            {winningLine}█
                          </div>
                          <div
                            style={{
                              position: "absolute",
                              top: 0,
                              left: 0,
                              right: 0,
                              fontFamily: bodyFont,
                              fontSize: "30px",
                              fontWeight: 600,
                              lineHeight: 1.4,
                              // Landed pop: scale-snap + a quick white glow the
                              // instant typing finishes — makes the payoff read
                              // as a hit, not just the cursor stopping.
                              color: COOKD_THEME.nothingWhite,
                              transform: `scale(${landedPunch})`,
                              transformOrigin: "left center",
                              textShadow: `0 0 ${interpolate(
                                landedFlash,
                                [0, 1],
                                [0, 24]
                              )}px rgba(255,255,255,${landedFlash * 0.9})`,
                            }}
                          >
                            {visibleText}
                            <span style={{ color: COOKD_THEME.textSecondary }}>
                              {randomScrambleChar}
                            </span>
                            <span
                              style={{
                                opacity: isTyping || frame % 20 < 10 ? 1 : 0,
                                color: COOKD_THEME.neonRed,
                                fontSize: "28px",
                              }}
                            >
                              █
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* Flash-cuts — a hard 2-frame white pop at the two "event" moments
          (the payoff landing, the outro starting) instead of another smooth
          fade. Cheap pattern-interrupt that reads as a beat, not a slide. */}
      {[revealStartFrame, outroStartFrame].map((cutFrame, i) => (
        <AbsoluteFill
          key={i}
          style={{
            backgroundColor: COOKD_THEME.nothingWhite,
            opacity: interpolate(frame, [cutFrame, cutFrame + 1, cutFrame + 3], [0, 0.85, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            zIndex: 350,
            pointerEvents: "none",
          }}
        />
      ))}

      {/* OUTRO — CTA badge, positioned within safe zone */}
      {(() => {
        if (frame < outroStartFrame) return null;

        const localFrame = frame - outroStartFrame;

        const captionIn = interpolate(localFrame, [0, 15], [0, 1], {
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });

        const fadeToBlack = interpolate(
          localFrame,
          [OUTRO_HOLD - 26, OUTRO_HOLD - 6],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        // Seamless-loop bookend: the last frame lands on the exact same
        // full-opacity red as frame 0's opening stinger, so an autoplay
        // loop reads as one continuous flash instead of a black→red jump
        // cut. Mirrors the intro's [0, 1, 4] → [1, 0.7, 0] decay in reverse.
        const loopFlash = interpolate(
          localFrame,
          [OUTRO_HOLD - 5, OUTRO_HOLD - 2, OUTRO_HOLD - 1],
          [0, 0.7, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        return (
          <>
            <AbsoluteFill
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                paddingBottom: SAFE_BOTTOM - 20,
                paddingLeft: SAFE_LEFT,
                paddingRight: SAFE_RIGHT,
                zIndex: 100,
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  background: "rgba(10, 10, 10, 0.85)",
                  border: `1px solid ${COOKD_THEME.nothingBorder}`,
                  borderRadius: "9999px",
                  padding: "16px 28px",
                  opacity: captionIn,
                  transform: `translateY(${interpolate(
                    captionIn,
                    [0, 1],
                    [20, 0]
                  )}px)`,
                }}
              >
                <svg width="26" height="26" viewBox="0 0 108 108" fill="none">
                  <circle cx="54" cy="54" r="28" fill="#FFFFFF" />
                  <path
                    fill="#000000"
                    fillRule="evenodd"
                    d="M63.73,45.51 A12,12 0 1,0 63.73,62.49 L61.31,60.07 A8.6,8.6 0 1,1 61.31,47.93 Z"
                  />
                </svg>
                <span
                  style={{
                    fontFamily: bodyFont,
                    fontSize: "22px",
                    fontWeight: 600,
                    color: COOKD_THEME.nothingWhite,
                  }}
                >
                  Cookd AI helped write this reply
                </span>
              </div>
            </AbsoluteFill>
            <AbsoluteFill
              style={{
                backgroundColor: COOKD_THEME.nothingBlack,
                opacity: fadeToBlack,
                zIndex: 300,
                pointerEvents: "none",
              }}
            />
            <AbsoluteFill
              style={{
                backgroundColor: COOKD_THEME.neonRed,
                opacity: loopFlash,
                zIndex: 301,
                pointerEvents: "none",
              }}
            />
          </>
        );
      })()}
    </AbsoluteFill>
  );
};
