import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { loadFont } from "@remotion/google-fonts/PlusJakartaSans";
import type { CookdShortProps } from "./types";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
});

const COOKD_THEME = {
  nothingBlack: "#000000",
  nothingWhite: "#FFFFFF",
  neonRed: "#FF003C",
  nothingSurface: "#050505",
  nothingBorder: "rgba(255, 255, 255, 0.1)",
  textSecondary: "rgba(255, 255, 255, 0.45)",
  successGreen: "#00FF66",
};

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

const BG_VARIANTS = [
  "radial-gradient(ellipse at 50% 0%, #1a1a1a 0%, #000000 100%)",
  "radial-gradient(ellipse at 22% 8%, #1d1418 0%, #000000 70%)",
  "radial-gradient(ellipse at 80% 12%, #13181d 0%, #000000 72%)",
  "radial-gradient(ellipse at 50% 100%, #191919 0%, #000000 82%)",
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

export const ProfileCardVideo: React.FC<CookdShortProps> = ({
  personName,
  winningLine,
  strategyLabel,
  keyDetail,
}) => {
  const frame = useCurrentFrame();

  const seed = seedFrom(personName + strategyLabel);
  const bgGradient = pick(BG_VARIANTS, seed);
  const avatarColor = getAvatarColor(personName);

  // --- TIMING (30 FPS) ---
  const hookEnd = 60; // 0-2s: Hook
  const bioStart = 60; // 2-4s: Her bio
  const openerStart = 120; // 4s+: Our opener
  const typingSpeed = 2;
  const typingDone = openerStart + (winningLine?.length || 0) * typingSpeed;
  const badgeStart = typingDone + 20;
  const outroStart = badgeStart + 60;

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
        padding: "60px 50px",
      }}
    >
      {/* ⚡ HOOK: 0-2s */}
      {frame < hookEnd && (
        <AbsoluteFill
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 200,
            opacity: interpolate(frame, [0, 5, 50, 60], [0, 1, 1, 0]),
          }}
        >
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
              gap: "24px",
            }}
          >
            <span
              style={{
                fontSize: "28px",
                fontWeight: 700,
                color: COOKD_THEME.textSecondary,
                letterSpacing: "2px",
              }}
            >
              MOST GUYS
            </span>
            <span
              style={{
                fontSize: "96px",
                fontWeight: 800,
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

      {/* 📋 PROFILE CARD: 2s+ */}
      {frame >= bioStart && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            width: "100%",
            maxWidth: "800px",
            opacity: interpolate(frame, [bioStart, bioStart + 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {/* Avatar */}
          <div
            style={{
              width: "100px",
              height: "100px",
              borderRadius: "50%",
              backgroundColor: avatarColor,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "44px",
              fontWeight: 700,
              border: `3px solid ${COOKD_THEME.nothingBorder}`,
              marginBottom: "20px",
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
              fontSize: "36px",
              fontWeight: 700,
              marginBottom: "8px",
            }}
          >
            {personName}
          </span>

          {/* Label */}
          <span
            style={{
              fontSize: "16px",
              fontWeight: 600,
              color: COOKD_THEME.textSecondary,
              letterSpacing: "2px",
              marginBottom: "12px",
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
                borderRadius: "16px",
                padding: "24px 32px",
                marginBottom: "32px",
                width: "100%",
                opacity: interpolate(
                  frame,
                  [bioStart + 10, bioStart + 25],
                  [0, 1],
                  {
                    extrapolateRight: "clamp",
                  }
                ),
              }}
            >
              <span
                style={{
                  fontSize: "28px",
                  fontWeight: 500,
                  lineHeight: 1.4,
                  color: COOKD_THEME.textSecondary,
                }}
              >
                &ldquo;{keyDetail}&rdquo;
              </span>
            </div>
          )}

          {/* Cookd reply label */}
          <span
            style={{
              fontSize: "16px",
              fontWeight: 600,
              color: COOKD_THEME.neonRed,
              letterSpacing: "2px",
              marginBottom: "12px",
              opacity: interpolate(
                frame,
                [openerStart - 15, openerStart],
                [0, 1],
                {
                  extrapolateRight: "clamp",
                }
              ),
            }}
          >
            COOKD REPLIED
          </span>

          {/* Winning opener */}
          {frame >= openerStart && winningLine && (
            <div
              style={{
                background: "rgba(255, 0, 60, 0.08)",
                border: `1px solid rgba(255, 0, 60, 0.3)`,
                borderRadius: "16px",
                padding: "28px 36px",
                width: "100%",
                boxShadow: `0 0 30px rgba(255, 0, 60, 0.1)`,
              }}
            >
              <span
                style={{
                  fontSize: "34px",
                  fontWeight: 600,
                  lineHeight: 1.4,
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
                marginTop: "24px",
                padding: "12px 24px",
                background: "rgba(0, 255, 102, 0.1)",
                border: `1px solid ${COOKD_THEME.successGreen}`,
                borderRadius: "999px",
                opacity: interpolate(
                  frame,
                  [badgeStart, badgeStart + 15],
                  [0, 1],
                  {
                    extrapolateRight: "clamp",
                  }
                ),
              }}
            >
              <span style={{ fontSize: "20px" }}>&#127919;</span>
              <span
                style={{
                  fontSize: "20px",
                  fontWeight: 700,
                  color: COOKD_THEME.successGreen,
                }}
              >
                {strategyLabel}
              </span>
            </div>
          )}
        </div>
      )}

      {/* 🎬 OUTRO CTA */}
      {frame >= outroStart && (
        <AbsoluteFill
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            paddingBottom: "80px",
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
              background: "rgba(5, 5, 5, 0.7)",
              border: `1px solid ${COOKD_THEME.nothingBorder}`,
              borderRadius: "999px",
              padding: "18px 32px",
            }}
          >
            <span style={{ fontSize: "26px" }}>&#10024;</span>
            <span
              style={{
                fontSize: "26px",
                fontWeight: 600,
                color: COOKD_THEME.nothingWhite,
              }}
            >
              Cookd AI &mdash; first moves that work
            </span>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/** Duration calculator for the ProfileCard composition (30 FPS). */
export function calcProfileCardDuration(winningLine: string): number {
  const typingDuration = (winningLine?.length || 0) * 2;
  const badgeDelay = 20;
  const outroDelay = 60;
  const outroHold = 90;
  return 120 + typingDuration + badgeDelay + outroDelay + outroHold; // ~12s
}
