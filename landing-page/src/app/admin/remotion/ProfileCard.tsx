import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as loadHeading } from "@remotion/google-fonts/SpaceGrotesk";
import { loadFont as loadBody } from "@remotion/google-fonts/DMSans";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import type { CookdShortProps } from "./types";

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

// Same safe zones as Composition.tsx — see the comment there for rationale.
const SAFE_TOP = 190;
const SAFE_BOTTOM = 340;
const SAFE_LEFT = 60;
const SAFE_RIGHT = 160;

// Pitch-black, single-accent backgrounds — no off-brand hues. Variety comes
// only from the vignette position, matching "strict dark mode, no compromises".
const BG_VARIANTS = [
  "radial-gradient(ellipse at 50% 0%, #0a0a0a 0%, #000000 100%)",
  "radial-gradient(ellipse at 15% 10%, #0a0a0a 0%, #000000 70%)",
  "radial-gradient(ellipse at 85% 10%, #0a0a0a 0%, #000000 70%)",
  "radial-gradient(ellipse at 50% 100%, #0a0a0a 0%, #000000 85%)",
];

function pick<T>(arr: T[], seed: number, salt = 0): T {
  return arr[(seed + salt) % arr.length];
}

function seedFrom(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = str.charCodeAt(i) + ((h << 5) - h);
  }
  return Math.abs(h);
}

// ── Icon (hand-inlined, heroicons-style outline path — no emoji) ──

const TargetIcon: React.FC<{ size?: number; color?: string }> = ({
  size = 18,
  color = "currentColor",
}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="9" stroke={color} strokeWidth={1.5} />
    <circle cx="12" cy="12" r="5" stroke={color} strokeWidth={1.5} />
    <circle cx="12" cy="12" r="1.5" fill={color} />
  </svg>
);

// ── Persistent logo watermark ──

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

export const ProfileCardVideo: React.FC<CookdShortProps> = ({
  personName,
  winningLine,
  strategyLabel,
  keyDetail,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const seed = seedFrom(personName + strategyLabel);
  const bgGradient = pick(BG_VARIANTS, seed);

  const hookEnd = 60;
  const bioStart = 60;
  const openerStart = 120;
  const typingSpeed = 2;
  const typingDone = openerStart + (winningLine?.length || 0) * typingSpeed;
  const badgeStart = typingDone + 20;
  const outroStart = badgeStart + 60;
  const OUTRO_HOLD = 90;
  const totalDuration = outroStart + OUTRO_HOLD;

  // Once the reply lands, the bio/name/avatar dim down so the payoff is the
  // one bright thing on screen — a focus-pull, not just another element at
  // the same brightness as everything before it.
  const focusDim =
    frame >= typingDone
      ? interpolate(frame, [typingDone, typingDone + 15], [1, 0.32], {
          extrapolateRight: "clamp",
        })
      : 1;

  // Landed pop: scale-snap + white glow the instant typing finishes — the
  // actual payoff, so it should read as a hit rather than the cursor stopping.
  // Capped so the overshoot can't push the line wider than its container.
  const landedPunch =
    frame < typingDone
      ? 1
      : Math.min(
          spring({
            frame: frame - typingDone,
            fps,
            config: { damping: 8, stiffness: 300, mass: 0.5 },
          }),
          1.06
        );
  const landedFlash = interpolate(
    frame,
    [typingDone, typingDone + 2, typingDone + 12],
    [0, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Badge "thunks" in with an overshoot pop instead of just fading.
  const badgePunch =
    frame < badgeStart
      ? 0
      : spring({
          frame: frame - badgeStart,
          fps,
          config: { damping: 9, stiffness: 260, mass: 0.6 },
        });

  return (
    <AbsoluteFill
      style={{
        fontFamily: bodyFont,
        color: COOKD_THEME.nothingWhite,
      }}
    >
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

      {/* Persistent logo watermark */}
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

      {/* HOOK: 0-2s */}
      {frame < hookEnd && (
        <AbsoluteFill
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 200,
            opacity: interpolate(frame, [0, 5, 50, 60], [0, 1, 1, 0]),
            paddingLeft: SAFE_LEFT,
            paddingRight: SAFE_RIGHT,
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "24px",
            }}
          >
            <span
              style={{
                fontFamily: monoFont,
                fontSize: "26px",
                fontWeight: 600,
                color: COOKD_THEME.textSecondary,
                letterSpacing: "2px",
              }}
            >
              MOST GUYS
            </span>
            <span
              style={{
                fontFamily: headingFont,
                fontSize: "96px",
                fontWeight: 700,
                color: COOKD_THEME.neonRed,
                transform: `scale(${interpolate(
                  frame,
                  [0, 30, 60],
                  [0.8, 1, 1.1]
                )})`,
              }}
            >
              &ldquo;hey&rdquo;
            </span>
          </div>
        </AbsoluteFill>
      )}

      {/* PROFILE CONTENT: full bleed, no card */}
      {frame >= bioStart && (
        <div
          style={{
            position: "absolute",
            top: SAFE_TOP,
            left: SAFE_LEFT,
            right: SAFE_RIGHT,
            bottom: SAFE_BOTTOM,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            opacity: interpolate(frame, [bioStart, bioStart + 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {/* Dims once the reply lands — a focus-pull so the payoff is the
              one bright thing on screen instead of staying level with the
              bio/name that came before it. */}
          <div style={{ opacity: focusDim, display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
          {/* Avatar — neutral chip, no rainbow palette (one accent only) */}
          <div
            style={{
              width: "90px",
              height: "90px",
              borderRadius: "50%",
              backgroundColor: COOKD_THEME.nothingSurface,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: headingFont,
              fontSize: "40px",
              fontWeight: 700,
              border: `1.5px solid ${COOKD_THEME.nothingBorder}`,
              marginBottom: "16px",
              transform: `scale(${interpolate(
                frame - bioStart,
                [0, 15],
                [0, 1],
                { extrapolateRight: "clamp" }
              )})`,
            }}
          >
            {personName.charAt(0).toUpperCase()}
          </div>

          {/* Name */}
          <span
            style={{
              fontFamily: headingFont,
              fontSize: "32px",
              fontWeight: 700,
              marginBottom: "6px",
            }}
          >
            {personName}
          </span>

          {/* Label */}
          <span
            style={{
              fontFamily: monoFont,
              fontSize: "14px",
              fontWeight: 600,
              color: COOKD_THEME.textSecondary,
              letterSpacing: "1.5px",
              marginBottom: "16px",
            }}
          >
            SHE SAYS IN HER BIO
          </span>

          {/* Bio quote */}
          {keyDetail && (
            <div
              style={{
                background: COOKD_THEME.nothingSurface,
                border: `1px solid ${COOKD_THEME.nothingBorder}`,
                borderRadius: "12px",
                padding: "20px 24px",
                marginBottom: "24px",
                width: "100%",
                opacity: interpolate(
                  frame,
                  [bioStart + 10, bioStart + 25],
                  [0, 1],
                  { extrapolateRight: "clamp" }
                ),
              }}
            >
              <span
                style={{
                  fontFamily: bodyFont,
                  fontSize: "24px",
                  fontWeight: 500,
                  lineHeight: 1.4,
                  color: COOKD_THEME.textSecondary,
                }}
              >
                &ldquo;{keyDetail}&rdquo;
              </span>
            </div>
          )}
          </div>

          {/* Cookd reply label */}
          <span
            style={{
              fontFamily: monoFont,
              fontSize: "14px",
              fontWeight: 600,
              color: COOKD_THEME.neonRed,
              letterSpacing: "1.5px",
              marginBottom: "10px",
              opacity: interpolate(
                frame,
                [openerStart - 15, openerStart],
                [0, 1],
                { extrapolateRight: "clamp" }
              ),
            }}
          >
            COOKD REPLIED
          </span>

          {/* Winning opener */}
          {frame >= openerStart && winningLine && (
            <div
              style={{
                background: "rgba(225, 29, 72, 0.08)",
                border: `1px solid rgba(225, 29, 72, 0.3)`,
                borderRadius: "12px",
                padding: "24px 28px",
                width: "100%",
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  fontFamily: bodyFont,
                  fontSize: "30px",
                  fontWeight: 600,
                  lineHeight: 1.4,
                  transform: `scale(${landedPunch})`,
                  transformOrigin: "left center",
                  textShadow: `0 0 ${interpolate(
                    landedFlash,
                    [0, 1],
                    [0, 24]
                  )}px rgba(255,255,255,${landedFlash * 0.9})`,
                }}
              >
                {winningLine.substring(
                  0,
                  Math.max(0, Math.floor((frame - openerStart) / typingSpeed))
                )}
                <span
                  style={{
                    color: COOKD_THEME.neonRed,
                    opacity: frame % 20 < 10 ? 1 : 0,
                  }}
                >
                  &#9608;
                </span>
              </span>
            </div>
          )}

          {/* Strategy badge */}
          {frame >= badgeStart && strategyLabel && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                marginTop: "20px",
                padding: "10px 20px",
                background: "rgba(0, 255, 102, 0.1)",
                border: `1px solid ${COOKD_THEME.successGreen}`,
                borderRadius: "9999px",
                opacity: interpolate(
                  frame,
                  [badgeStart, badgeStart + 10],
                  [0, 1],
                  { extrapolateRight: "clamp" }
                ),
                transform: `scale(${badgePunch})`,
              }}
            >
              <TargetIcon size={18} color={COOKD_THEME.successGreen} />
              <span
                style={{
                  fontFamily: monoFont,
                  fontSize: "16px",
                  fontWeight: 600,
                  letterSpacing: "0.5px",
                  color: COOKD_THEME.successGreen,
                }}
              >
                {strategyLabel}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Flash-cuts — a hard 2-frame white pop at the payoff landing and the
          outro starting, instead of another smooth fade. */}
      {[typingDone, outroStart].map((cutFrame, i) => (
        <AbsoluteFill
          key={i}
          style={{
            backgroundColor: COOKD_THEME.nothingWhite,
            opacity: interpolate(
              frame,
              [cutFrame, cutFrame + 1, cutFrame + 3],
              [0, 0.85, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            zIndex: 350,
            pointerEvents: "none",
          }}
        />
      ))}

      {/* OUTRO CTA — inside safe zone */}
      {frame >= outroStart && (
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
            opacity: interpolate(frame, [outroStart, outroStart + 15], [0, 1], {
              extrapolateRight: "clamp",
            }),
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
              Cookd AI &mdash; first moves that work
            </span>
          </div>
        </AbsoluteFill>
      )}

      {/* Seamless-loop bookend: fade to black, then the last frame lands on
          the exact same full-opacity red as frame 0's opening stinger, so an
          autoplay loop reads as one continuous flash instead of a jump cut. */}
      <AbsoluteFill
        style={{
          backgroundColor: COOKD_THEME.nothingBlack,
          opacity: interpolate(
            frame - outroStart,
            [OUTRO_HOLD - 26, OUTRO_HOLD - 6],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
          zIndex: 300,
          pointerEvents: "none",
        }}
      />
      <AbsoluteFill
        style={{
          backgroundColor: COOKD_THEME.neonRed,
          opacity: interpolate(
            frame - outroStart,
            [OUTRO_HOLD - 5, OUTRO_HOLD - 2, OUTRO_HOLD - 1],
            [0, 0.7, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
          zIndex: 301,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

/** Duration calculator for the ProfileCard composition (30 FPS). */
export function calcProfileCardDuration(winningLine: string): number {
  const typingDuration = (winningLine?.length || 0) * 2;
  const badgeDelay = 20;
  const outroDelay = 60;
  const outroHold = 90;
  return 120 + typingDuration + badgeDelay + outroDelay + outroHold;
}
