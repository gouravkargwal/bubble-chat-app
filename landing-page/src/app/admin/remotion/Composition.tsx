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
import { loadFont } from "@remotion/google-fonts/PlusJakartaSans";
import { CookdShortProps } from "./types";
import { generateHook } from "./hookGenerator";

// 🔲 EXACT TYPOGRAPHY FROM Typography.kt
const { fontFamily } = loadFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
});

// 🎨 EXACT COLORS FROM JETPACK COMPOSE
const COOKD_THEME = {
  nothingBlack: "#000000",
  nothingWhite: "#FFFFFF",
  neonRed: "#FF003C",
  nothingSurface: "#050505",
  nothingBorder: "rgba(255, 255, 255, 0.1)",
  textSecondary: "rgba(255, 255, 255, 0.45)",
  successGreen: "#00FF66",
};

const SCRAMBLE_CHARS = "!<>-_\\/[]{}—=+*^?#_";

// ── AVATAR COLORS (deterministic from personName) ──
const AVATAR_PALETTE = [
  "#FF003C",
  "#FF6B35",
  "#FFD23F",
  "#00FF66",
  "#00C9FF",
  "#8B5CF6",
  "#FF007F",
  "#00F5D4",
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_PALETTE[Math.abs(hash) % AVATAR_PALETTE.length];
}

// ── DETERMINISTIC VARIETY (breaks the "obviously templated" look) ──
// Same input → same output (renders are reproducible), but different people
// yield different backgrounds / copy, so the feed doesn't look mass-produced.
function seedFrom(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = str.charCodeAt(i) + ((h << 5) - h);
  }
  return Math.abs(h);
}

function pick<T>(arr: T[], seed: number, salt = 0): T {
  return arr[(seed + salt) % arr.length];
}

// Subtle dark-gradient variants — keeps the brand mood, varies the frame.
const BG_VARIANTS = [
  "radial-gradient(ellipse at 50% 0%, #1a1a1a 0%, #000000 100%)",
  "radial-gradient(ellipse at 22% 8%, #1d1418 0%, #000000 70%)",
  "radial-gradient(ellipse at 80% 12%, #13181d 0%, #000000 72%)",
  "radial-gradient(ellipse at 50% 100%, #191919 0%, #000000 82%)",
];

// "Cookd is working" labels — human, curious, never clinical.
const THINKING_LABELS = [
  "COOKD IS COOKING",
  "READING THE VIBE",
  "FINDING YOUR MOVE",
  "CRAFTING THE REPLY",
];

// Payoff labels — outcome-driven, screams "copy this", not "target acquired".
const REVEAL_LABELS = ["SEND THIS 👇", "YOUR MOVE 🔥", "USE THIS ONE", "COPY THIS 👇"];

// Relatable status lines shown during the (now brief) thinking beat.
const THINKING_LINES = [
  ["Reading their last message…", "Matching your energy…"],
  ["Catching the vibe…", "Finding the perfect angle…"],
  ["Reading between the lines…", "Building your comeback…"],
  ["Feeling out the tone…", "Lining up the reply…"],
];

// ── TYPING DOTS COMPONENT ──
const TypingDots: React.FC<{ frame: number; fps: number }> = ({
  frame,
  fps,
}) => {
  return (
    <div
      style={{
        display: "flex",
        gap: "12px",
        padding: "20px 30px",
        alignItems: "center",
      }}
    >
      {[0, 1, 2].map((i) => {
        const dotSpring = spring({
          frame: frame - i * 4,
          fps,
          config: { damping: 12, mass: 0.5 },
        });
        return (
          <div
            key={i}
            style={{
              width: "14px",
              height: "14px",
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
};

// ── PHONE MOCKUP FRAME ──
const PhoneFrame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      width: "100%",
      height: "100%",
      display: "flex",
      flexDirection: "column",
      borderRadius: "48px",
      border: "3px solid rgba(255, 255, 255, 0.15)",
      overflow: "hidden",
      position: "relative",
      background: COOKD_THEME.nothingBlack,
    }}
  >
    {/* Notch */}
    <div
      style={{
        position: "absolute",
        top: 0,
        left: "50%",
        transform: "translateX(-50%)",
        width: "180px",
        height: "28px",
        backgroundColor: COOKD_THEME.nothingBlack,
        borderBottomLeftRadius: "18px",
        borderBottomRightRadius: "18px",
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px",
      }}
    >
      <div
        style={{
          width: "10px",
          height: "10px",
          borderRadius: "50%",
          backgroundColor: "#1a1a1a",
          border: "1px solid #333",
        }}
      />
    </div>
    {children}
  </div>
);

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

  // Generate dynamic hook text for the first 2 seconds
  const hookText = generateHook({
    hookStyle,
    personName,
    messages,
    winningLine,
    strategyLabel,
  });

  // Break the hook into words, flagging any word inside "quotes" so it can be
  // emphasized in neon red — that's the emotional beat the eye should catch.
  const hookWords: { text: string; emph: boolean }[] = [];
  hookText.split('"').forEach((segment, segIndex) => {
    const emph = segIndex % 2 === 1; // odd segments were inside quotes
    const words = segment.split(/\s+/).filter((w) => w.length > 0);
    words.forEach((word, wi) => {
      // Re-attach the quote glyphs to the emphasized phrase so it still reads.
      let text = word;
      if (emph && wi === 0) text = `"${text}`;
      if (emph && wi === words.length - 1) text = `${text}"`;
      hookWords.push({ text, emph });
    });
  });

  // Seeded, per-person variety so the feed never looks mass-produced.
  const seed = seedFrom(personName + strategyLabel);
  const bgGradient = pick(BG_VARIANTS, seed);
  const thinkingLabel = pick(THINKING_LABELS, seed, 1);
  const revealLabel = pick(REVEAL_LABELS, seed, 2);
  const thinkingLines = pick(THINKING_LINES, seed, 3);

  // --- CORE TIMING MATH (30 FPS) — tuned for RETENTION ---
  // Rule: the payoff (winning line) must land by ~8s or viewers swipe.
  // 0. Hook: first 60 frames (2s)
  // 1. Messages arrive fast — ~0.9s each (no dead air between them)
  const MSG_PACE = 28;
  const chatStartFrame = 65; // after hook + 5 frame gap
  const analyzeStartFrame = chatStartFrame + messages.length * MSG_PACE;
  // 2. Brief tension beat — 0.6s, builds anticipation instead of making you wait
  const ANALYZE_FRAMES = 18;
  const revealStartFrame = analyzeStartFrame + ANALYZE_FRAMES;
  // 3. Snappy typing (2 frames/char) so the payoff hits hard and quick
  const typingSpeed = 2;
  const typingDuration = winningLine.length * typingSpeed;
  // 4. Let the payoff breathe (~2.5s) before the outro
  const outroStartFrame = revealStartFrame + typingDuration + 75;

  return (
    <AbsoluteFill
      style={{
        background: bgGradient,
        fontFamily,
        color: COOKD_THEME.nothingWhite,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "40px",
      }}
    >
      {/* 🎙️ MASTER AUDIO — kept quiet so a creator can drop a trending sound
          on top later. Nothing in the video RELIES on audio to be understood:
          the whole story reads with sound off (silent-first for organic reach). */}
      {voiceoverAudio && <Audio src={voiceoverAudio} volume={0.8} />}

      {/* 🪝 HOOK FRAME (first ~2 seconds — 60 frames at 30fps) */}
      {frame < 60 && (
        <AbsoluteFill
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 200,
            // Snap in fast (attention peaks instantly), hold, clean exit.
            opacity: interpolate(frame, [0, 5, 50, 60], [0, 1, 1, 0]),
            // Confident punch-in, then a quick pop on the way out.
            transform: `scale(${interpolate(
              frame,
              [0, 50, 60],
              [1, 1.05, 1.14]
            )})`,
          }}
        >
          {/* ⚡ COLOR FLASH PATTERN INTERRUPT (first 3 frames) */}
          {frame < 4 && (
            <AbsoluteFill
              style={{
                backgroundColor: COOKD_THEME.neonRed,
                opacity: interpolate(frame, [0, 1, 4], [1, 0.7, 0]),
              }}
            />
          )}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "36px",
            }}
          >
            {/* Word-by-word kinetic reveal — legible almost immediately,
                each word springs up with a touch of overshoot for energy. */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "center",
                alignItems: "baseline",
                maxWidth: "92%",
                columnGap: "20px",
                rowGap: "6px",
                padding: "0 20px",
              }}
            >
              {hookWords.map((word, i) => {
                const wordSpring = spring({
                  frame: frame - i * 1.6,
                  fps,
                  config: { damping: 12, stiffness: 200, mass: 0.6 },
                });
                return (
                  <span
                    key={i}
                    style={{
                      display: "inline-block",
                      fontSize: "84px",
                      fontWeight: 800,
                      lineHeight: 1.05,
                      letterSpacing: "-2px",
                      color: word.emph
                        ? COOKD_THEME.neonRed
                        : COOKD_THEME.nothingWhite,
                      textShadow: word.emph
                        ? "0 0 40px rgba(255, 0, 60, 0.45)"
                        : "none",
                      opacity: interpolate(wordSpring, [0, 0.8], [0, 1]),
                      transform: `translateY(${interpolate(
                        wordSpring,
                        [0, 1],
                        [28, 0]
                      )}px) scale(${interpolate(
                        wordSpring,
                        [0, 1],
                        [0.86, 1]
                      )})`,
                    }}
                  >
                    {word.text}
                  </span>
                );
              })}
            </div>

            {/* Neon accent line — stamps in under the text for a punchy beat
                (replaces the old "loading bar", which read as waiting). */}
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
                height: "6px",
                background: COOKD_THEME.neonRed,
                borderRadius: "3px",
                boxShadow: "0 0 24px rgba(255, 0, 60, 0.6)",
              }}
            />
          </div>
        </AbsoluteFill>
      )}

      {/* Phone mockup containing chat UI */}
      {frame >= 55 && (
        <div
          style={{
            width: "90%",
            maxWidth: "860px",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            // Remotion's interpolate() EXTENDS past its range by default —
            // it does not clamp. This div has no upper frame bound (stays
            // mounted for the rest of the video), so without clamping here,
            // translateY kept extrapolating negative forever after frame 70,
            // dragging the entire phone mockup upward and off-canvas as the
            // video went on. That was the real bug — clamp both explicitly.
            opacity: interpolate(frame, [55, 65], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            transform: `translateY(${interpolate(
              frame,
              [55, 70],
              [40, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            )}px)`,
          }}
        >
          <PhoneFrame>
            {/* Chat header — reads like a REAL messaging app (contact + online),
                not a surveillance HUD. Native feel = shares, not "this is an ad".
                flexShrink: 0 — this is FIXED chrome; it must never be squeezed
                or displaced by however tall the scrolling body gets. */}
            <div
              style={{
                display: "flex",
                flexShrink: 0,
                justifyContent: "space-between",
                alignItems: "center",
                background: COOKD_THEME.nothingSurface,
                padding: "24px 32px",
                borderBottom: `1px solid ${COOKD_THEME.nothingBorder}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                {/* Contact avatar */}
                <div
                  style={{
                    width: "56px",
                    height: "56px",
                    borderRadius: "50%",
                    backgroundColor: getAvatarColor(personName),
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "26px",
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {personName.charAt(0).toUpperCase()}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <span
                    style={{
                      fontSize: "28px",
                      fontWeight: 700,
                      letterSpacing: "-0.5px",
                    }}
                  >
                    {personName}
                  </span>
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      fontSize: "18px",
                      fontWeight: 600,
                      color: COOKD_THEME.successGreen,
                    }}
                  >
                    <span
                      style={{
                        width: "10px",
                        height: "10px",
                        borderRadius: "50%",
                        backgroundColor: COOKD_THEME.successGreen,
                      }}
                    />
                    online
                  </span>
                </div>
              </div>
              {/* Video-call glyph — pure native chrome */}
              <span
                style={{
                  color: COOKD_THEME.textSecondary,
                  fontSize: "28px",
                }}
              >
                📹
              </span>
            </div>

            {/* Chat Messages BODY — the ONLY part of the phone that moves.
                Header above and footer below are flexShrink:0 (fixed chrome);
                this is flex:1 so it's locked to exactly the leftover space
                between them, no matter how much is inside it.
                minHeight: 0 overrides the flex-item default of min-height:auto —
                without it, this box refuses to shrink below its own content
                size and grows past its allotted space instead of clipping
                internally (pushing the fixed header/footer out of place).
                overflow: hidden + justifyContent: flex-end is what turns
                "more messages than fit" into a real scroll: new messages sit
                at the bottom, older ones get clipped off the top — the box
                itself never resizes. */}
            <div
              style={{
                flex: 1,
                minHeight: 0,
                display: "flex",
                flexDirection: "column",
                justifyContent: "flex-end",
                margin: "40px 32px",
                overflow: "hidden",
              }}
            >
              {messages.map((msg, index) => {
                const entryFrame = chatStartFrame + index * MSG_PACE;
                const isThem = msg.sender === "them";
                // Short "typing…" tease (10 frames) — enough to feel live,
                // not enough to stall the pace.
                const DOTS_WINDOW = 10;
                const showTypingDots =
                  frame >= entryFrame - DOTS_WINDOW && frame < entryFrame;

                if (frame < entryFrame - DOTS_WINDOW) return null;

                return (
                  <React.Fragment key={index}>
                    {/* Typing dots indicator before message */}
                    {showTypingDots && (
                      <div
                        style={{
                          display: "flex",
                          justifyContent: isThem ? "flex-start" : "flex-end",
                        }}
                      >
                        {isThem && (
                          <div
                            style={{
                              width: "44px",
                              height: "44px",
                              borderRadius: "50%",
                              backgroundColor: getAvatarColor(personName),
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "20px",
                              fontWeight: 700,
                              marginRight: "12px",
                              flexShrink: 0,
                            }}
                          >
                            {personName.charAt(0).toUpperCase()}
                          </div>
                        )}
                        <TypingDots
                          frame={frame - (entryFrame - DOTS_WINDOW)}
                          fps={fps}
                        />
                        {!isThem && (
                          <div
                            style={{
                              width: "44px",
                              height: "44px",
                              borderRadius: "50%",
                              backgroundColor: COOKD_THEME.neonRed,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "20px",
                              fontWeight: 700,
                              marginLeft: "12px",
                              flexShrink: 0,
                            }}
                          >
                            Y
                          </div>
                        )}
                      </div>
                    )}

                    {/* Message bubble */}
                    {frame >= entryFrame &&
                      (() => {
                        // Monotonic ease (no bounce) that fully settles in ~10
                        // frames — the upward growth IS the scroll, and it
                        // finishes before the next message lands at MSG_PACE.
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
                              // Grow the row height from 0 → full: older
                              // messages get pushed up smoothly, newest stays
                              // pinned to the bottom. 600px comfortably exceeds
                              // any single bubble so tall ones aren't clipped.
                              maxHeight: `${interpolate(
                                reveal,
                                [0, 1],
                                [0, 600]
                              )}px`,
                              overflow: "hidden",
                              paddingTop: `${interpolate(
                                reveal,
                                [0, 1],
                                [0, 28]
                              )}px`,
                            }}
                          >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "flex-end",
                              gap: "12px",
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
                            {/* Avatar for "them" messages */}
                            {isThem && (
                              <div
                                style={{
                                  width: "44px",
                                  height: "44px",
                                  borderRadius: "50%",
                                  backgroundColor: getAvatarColor(personName),
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  fontSize: "20px",
                                  fontWeight: 700,
                                  flexShrink: 0,
                                  border: `2px solid ${COOKD_THEME.nothingBorder}`,
                                }}
                              >
                                {personName.charAt(0).toUpperCase()}
                              </div>
                            )}

                            <div
                              style={{
                                maxWidth: "75%",
                                padding: "24px 32px",
                                fontSize: "28px",
                                lineHeight: 1.4,
                                backgroundColor: isThem
                                  ? COOKD_THEME.nothingSurface
                                  : "rgba(255, 0, 60, 0.08)",
                                border: `1px solid ${
                                  isThem
                                    ? COOKD_THEME.nothingBorder
                                    : "rgba(255, 0, 60, 0.2)"
                                }`,
                                color: COOKD_THEME.nothingWhite,
                                borderRadius: isThem
                                  ? "4px 20px 20px 20px"
                                  : "20px 4px 20px 20px",
                                fontWeight: 500,
                              }}
                            >
                              {msg.text}
                            </div>

                            {/* Avatar for "you" messages */}
                            {!isThem && (
                              <div
                                style={{
                                  width: "44px",
                                  height: "44px",
                                  borderRadius: "50%",
                                  backgroundColor: COOKD_THEME.neonRed,
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  fontSize: "20px",
                                  fontWeight: 700,
                                  flexShrink: 0,
                                  border: `2px solid rgba(255, 0, 60, 0.4)`,
                                }}
                              >
                                Y
                              </div>
                            )}
                          </div>
                          </div>
                        );
                      })()}
                  </React.Fragment>
                );
              })}

              {/* ⚡ VIRAL AI GENERATION BLOCK */}
              {(() => {
                if (frame < analyzeStartFrame) return null;

                const isAnalyzing = frame < revealStartFrame;
                const charsToShow = Math.max(
                  0,
                  Math.floor((frame - revealStartFrame) / typingSpeed)
                );
                const visibleText = winningLine.substring(0, charsToShow);
                const isTyping =
                  charsToShow < winningLine.length && !isAnalyzing;
                const randomScrambleChar = isTyping
                  ? SCRAMBLE_CHARS[
                      Math.floor(random(frame) * SCRAMBLE_CHARS.length)
                    ]
                  : "";
                // Confidence races to 99% across the brief thinking beat —
                // motion that builds anticipation instead of a dead spinner.
                const calcProgress = Math.min(
                  99,
                  Math.floor(((frame - analyzeStartFrame) / ANALYZE_FRAMES) * 100)
                );

                // Slide the AI block up fast so it never stalls the pace.
                const aiReveal = interpolate(
                  frame - analyzeStartFrame,
                  [0, 10],
                  [0, 1],
                  { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }
                );

                return (
                  <div
                    style={{
                      maxHeight: `${interpolate(aiReveal, [0, 1], [0, 900])}px`,
                      overflow: "hidden",
                      paddingTop: `${interpolate(aiReveal, [0, 1], [0, 40])}px`,
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
                      gap: "24px",
                      background: COOKD_THEME.nothingSurface,
                      padding: "36px 40px",
                      border: `1px solid ${
                        isAnalyzing
                          ? COOKD_THEME.textSecondary
                          : COOKD_THEME.neonRed
                      }`,
                      boxShadow: isAnalyzing
                        ? "none"
                        : `0 0 40px rgba(255, 0, 60, 0.15)`,
                      borderRadius: "12px",
                    }}
                  >
                    {/* Header */}
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        borderBottom: `1px solid ${COOKD_THEME.nothingBorder}`,
                        paddingBottom: "16px",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "26px",
                          color: isAnalyzing
                            ? COOKD_THEME.textSecondary
                            : COOKD_THEME.neonRed,
                          fontWeight: 800,
                          letterSpacing: "1px",
                        }}
                      >
                        {isAnalyzing ? thinkingLabel : revealLabel}
                      </span>
                      {!isAnalyzing && (
                        <span
                          style={{
                            fontSize: "18px",
                            color: COOKD_THEME.nothingBlack,
                            backgroundColor: COOKD_THEME.successGreen,
                            padding: "4px 12px",
                            fontWeight: 800,
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
                          gap: "24px",
                        }}
                      >
                        {/* AI Network Pulse - 3 concentric circles */}
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "40px",
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
                                  width: `${20 + i * 16}px`,
                                  height: `${20 + i * 16}px`,
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
                            color: COOKD_THEME.textSecondary,
                            display: "flex",
                            flexDirection: "column",
                            gap: "10px",
                            fontSize: "24px",
                            fontWeight: 500,
                          }}
                        >
                          <div>{thinkingLines[0]}</div>
                          <div>{thinkingLines[1]}</div>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "10px",
                            }}
                          >
                            <span>Confidence</span>
                            <span
                              style={{
                                color: COOKD_THEME.successGreen,
                                fontWeight: 800,
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
                          gap: "16px",
                          alignItems: "flex-start",
                        }}
                      >
                        {/* Sparkle — "here's the magic line", not a crosshair */}
                        <div
                          style={{
                            width: "48px",
                            height: "48px",
                            borderRadius: "50%",
                            backgroundColor: "rgba(0, 255, 102, 0.12)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "24px",
                            flexShrink: 0,
                            marginTop: "4px",
                          }}
                        >
                          ✨
                        </div>
                        <div style={{ flex: 1, position: "relative" }}>
                          {/* Ghost: the FULL winning line, invisible, reserves
                              the final box height up front. This is what stops
                              the layout from moving as characters type in —
                              only the overlaid text below grows into the space
                              that's already there; nothing above it reflows. */}
                          <div
                            style={{
                              fontSize: "36px",
                              fontWeight: 600,
                              lineHeight: 1.4,
                              visibility: "hidden",
                            }}
                            aria-hidden
                          >
                            {winningLine}
                          </div>
                          <div
                            style={{
                              position: "absolute",
                              top: 0,
                              left: 0,
                              right: 0,
                              fontSize: "36px",
                              fontWeight: 600,
                              lineHeight: 1.4,
                              color: COOKD_THEME.nothingWhite,
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
                                fontSize: "32px",
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

            {/* Subtext Footer — fixed chrome, same contract as the header. */}
            <div
              style={{
                display: "flex",
                flexShrink: 0,
                justifyContent: "space-between",
                alignItems: "center",
                borderTop: `1px solid ${COOKD_THEME.nothingBorder}`,
                padding: "28px 32px",
                fontSize: "18px",
                color: COOKD_THEME.textSecondary,
                fontWeight: 600,
              }}
            >
              <div>Cookd AI ✨</div>
              <div>your wingman, in your pocket</div>
            </div>
          </PhoneFrame>
        </div>
      )}

      {/* 🎬 SOFT-CTA OUTRO — a small caption over the still-visible chat,
          not a full-screen ad takeover. Native feel = it plays like a
          creator's own caption, not a download prompt, so it doesn't kill
          completion rate. The phone/chat stays on screen behind this. */}
      {(() => {
        if (frame < outroStartFrame) return null;

        const localFrame = frame - outroStartFrame;
        const OUTRO_HOLD = 120; // matches the +120 tail in calcDuration

        // Caption fades/slides in from the bottom third — like a subtitle.
        const captionIn = interpolate(localFrame, [0, 15], [0, 1], {
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });

        // Whole frame fades to black only in the final beat, so the cut
        // feels like a natural close instead of a hard ad-stinger.
        const fadeToBlack = interpolate(
          localFrame,
          [OUTRO_HOLD - 20, OUTRO_HOLD],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        return (
          <>
            <AbsoluteFill
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                paddingBottom: "90px",
                zIndex: 100,
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  background: "rgba(5, 5, 5, 0.7)",
                  border: `1px solid ${COOKD_THEME.nothingBorder}`,
                  borderRadius: "999px",
                  padding: "18px 32px",
                  opacity: captionIn,
                  transform: `translateY(${interpolate(
                    captionIn,
                    [0, 1],
                    [20, 0]
                  )}px)`,
                }}
              >
                <span style={{ fontSize: "26px" }}>✨</span>
                <span
                  style={{
                    fontSize: "26px",
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
          </>
        );
      })()}
    </AbsoluteFill>
  );
};
