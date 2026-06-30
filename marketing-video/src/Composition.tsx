import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  random,
  Img,
  staticFile,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/PlusJakartaSans";
import { CookdShortProps } from "./types";

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

const SCRAMBLE_CHARS = "!<>-_\\\\/[]{}—=+*^?#_";

export const CookdChatShortVideo: React.FC<CookdShortProps> = ({
  personName,
  messages,
  winningLine,
  strategyLabel,
  voiceoverAudio,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // --- CORE TIMING MATH (30 FPS) ---
  // 1. Give 1.5 seconds (45 frames) per message for reading time
  const analyzeStartFrame = 30 + messages.length * 45;
  // 2. Hold the "Analyzing..." HUD for 2 full seconds (60 frames)
  const revealStartFrame = analyzeStartFrame + 60;
  // 3. Slower typing speed (3 frames per character)
  const typingSpeed = 3;
  const typingDuration = winningLine.length * typingSpeed;
  // 4. Wait 3 full seconds (90 frames) AFTER typing finishes before the splash screen
  const outroStartFrame = revealStartFrame + typingDuration + 90;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COOKD_THEME.nothingBlack,
        fontFamily, // Uses Plus Jakarta Sans globally
        color: COOKD_THEME.nothingWhite,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "100px 60px",
      }}
    >
      {/* 🎙️ MASTER AUDIO */}
      {voiceoverAudio && <Audio src={voiceoverAudio} />}

      {/* App Header Widget */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: COOKD_THEME.nothingSurface,
          padding: "30px 40px",
          border: `1px solid ${COOKD_THEME.nothingBorder}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <div
            style={{
              width: "16px",
              height: "16px",
              backgroundColor: COOKD_THEME.neonRed,
              opacity: frame % 30 < 15 ? 1 : 0.2, // Slower hardware blink
            }}
          />
          <span
            style={{ fontSize: "36px", fontWeight: 800, letterSpacing: "-1px" }}
          >
            COOKD_AI // CHAT_LOG
          </span>
        </div>
        <span
          style={{
            color: COOKD_THEME.textSecondary,
            fontSize: "24px",
            fontWeight: 600,
          }}
        >
          [ID: {personName.toUpperCase()}]
        </span>
      </div>

      {/* Chat Bubbles */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: "40px",
          margin: "60px 0",
        }}
      >
        {messages.map((msg, index) => {
          const entryFrame = 15 + index * 45;
          const popScale = spring({
            frame: frame - entryFrame,
            fps,
            config: { damping: 14, mass: 0.9 },
          });

          if (frame < entryFrame) return null;

          const isThem = msg.sender === "them";
          return (
            <div
              key={index}
              style={{
                display: "flex",
                justifyContent: isThem ? "flex-start" : "flex-end",
                transform: `scale(${popScale})`,
                opacity: interpolate(frame - entryFrame, [0, 5], [0, 1]),
              }}
            >
              <div
                style={{
                  maxWidth: "85%",
                  padding: "35px 45px",
                  fontSize: "34px",
                  lineHeight: 1.4,
                  backgroundColor: isThem
                    ? COOKD_THEME.nothingSurface
                    : COOKD_THEME.nothingBlack,
                  border: `1px solid ${COOKD_THEME.nothingBorder}`,
                  color: COOKD_THEME.nothingWhite,
                  borderRadius: "8px",
                  fontWeight: 500,
                }}
              >
                {msg.text}
              </div>
            </div>
          );
        })}

        {/* ⚡ VIRAL AI GENERATION BLOCK */}
        {(() => {
          if (frame < analyzeStartFrame) return null;

          const isAnalyzing = frame < revealStartFrame;
          const charsToShow = Math.max(
            0,
            Math.floor((frame - revealStartFrame) / typingSpeed),
          );
          const visibleText = winningLine.substring(0, charsToShow);
          const isTyping = charsToShow < winningLine.length && !isAnalyzing;
          const randomScrambleChar = isTyping
            ? SCRAMBLE_CHARS[Math.floor(random(frame) * SCRAMBLE_CHARS.length)]
            : "";
          const calcProgress = Math.min(
            99,
            Math.floor(((frame - analyzeStartFrame) / 60) * 100),
          );

          return (
            <div
              style={{
                marginTop: "60px",
                display: "flex",
                flexDirection: "column",
                width: "100%",
                gap: "30px",
                background: COOKD_THEME.nothingSurface,
                padding: "50px",
                border: `1px solid ${
                  isAnalyzing ? COOKD_THEME.textSecondary : COOKD_THEME.neonRed
                }`,
                boxShadow: isAnalyzing
                  ? "none"
                  : `0 0 40px rgba(255, 0, 60, 0.15)`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  borderBottom: `1px solid ${COOKD_THEME.nothingBorder}`,
                  paddingBottom: "20px",
                }}
              >
                <span
                  style={{
                    fontSize: "32px",
                    color: isAnalyzing
                      ? COOKD_THEME.textSecondary
                      : COOKD_THEME.neonRed,
                    fontWeight: 800,
                    letterSpacing: "1px",
                  }}
                >
                  {isAnalyzing ? "SYS_ANALYZING..." : "TARGET_LOCKED"}
                </span>
                {!isAnalyzing && (
                  <span
                    style={{
                      fontSize: "22px",
                      color: COOKD_THEME.nothingBlack,
                      backgroundColor: COOKD_THEME.successGreen,
                      padding: "4px 12px",
                      fontWeight: 800,
                    }}
                  >
                    {strategyLabel}
                  </span>
                )}
              </div>

              <div
                style={{
                  fontSize: isAnalyzing ? "26px" : "44px",
                  fontWeight: 600,
                  lineHeight: 1.4,
                  color: COOKD_THEME.nothingWhite,
                }}
              >
                {isAnalyzing ? (
                  <div
                    style={{
                      color: COOKD_THEME.textSecondary,
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    <div>
                      &gt; TARGET_ENGAGEMENT:{" "}
                      <span style={{ color: COOKD_THEME.neonRed }}>LOW</span>
                    </div>
                    <div>&gt; INITIATING_PATTERN_INTERRUPT...</div>
                    <div>
                      &gt; CALCULATING_WIN_PROBABILITY:{" "}
                      <span style={{ color: COOKD_THEME.nothingWhite }}>
                        {calcProgress}%
                      </span>
                    </div>
                    <div
                      style={{
                        width: "100%",
                        height: "4px",
                        background: COOKD_THEME.nothingBorder,
                        marginTop: "10px",
                      }}
                    >
                      <div
                        style={{
                          width: `${calcProgress}%`,
                          height: "100%",
                          background: COOKD_THEME.textSecondary,
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  <>
                    "{visibleText}
                    <span style={{ color: COOKD_THEME.textSecondary }}>
                      {randomScrambleChar}
                    </span>
                    "
                    <span
                      style={{
                        opacity: isTyping || frame % 20 < 10 ? 1 : 0,
                        color: COOKD_THEME.neonRed,
                      }}
                    >
                      █
                    </span>
                  </>
                )}
              </div>
            </div>
          );
        })()}
      </div>

      {/* Subtext Footer */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderTop: `1px solid ${COOKD_THEME.nothingBorder}`,
          paddingTop: "40px",
          fontSize: "24px",
          color: COOKD_THEME.textSecondary,
          fontWeight: 600,
        }}
      >
        <div>SYSTEM // COOKD_APP</div>
        <div>
          INVITE:{" "}
          <span style={{ color: COOKD_THEME.nothingWhite, fontWeight: 800 }}>
            COOKD100
          </span>
        </div>
      </div>

      {/* 🎬 THE VIRAL OUTRO SPLASH SCREEN (Google Play CTA) */}
      {(() => {
        if (frame < outroStartFrame) return null;

        const outroSlide = spring({
          frame: frame - outroStartFrame,
          fps,
          config: { damping: 16, stiffness: 90 }, // Slower, smoother slide up
        });

        return (
          <AbsoluteFill
            style={{
              backgroundColor: COOKD_THEME.nothingBlack,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              transform: `translateY(${interpolate(outroSlide, [0, 1], [1920, 0])}px)`,
              zIndex: 100, // Forces the splash screen to cover the chat UI completely
            }}
          >
            {/* 🖼️ ACTUAL APP SVG LOGO */}
            <Img
              src={staticFile("logo.svg")} // Reads directly from marketing-video/public/logo.svg
              style={{
                width: "240px",
                height: "240px",
                borderRadius: "56px",
                marginBottom: "60px",
                border: `2px solid ${COOKD_THEME.nothingBorder}`,
                backgroundColor: COOKD_THEME.nothingSurface,
              }}
            />

            <h1
              style={{
                fontSize: "90px",
                fontWeight: 800,
                margin: "0 0 20px 0",
              }}
            >
              Cookd AI
            </h1>
            <p
              style={{
                fontSize: "40px",
                color: COOKD_THEME.textSecondary,
                fontFamily: "monospace",
                margin: "0 0 80px 0",
                letterSpacing: "2px",
              }}
            >
              DATING_COACH // V2.0
            </p>

            {/* GOOGLE PLAY EXCLUSIVE BADGE */}
            <div
              style={{
                display: "flex",
                gap: "30px",
                marginBottom: "100px",
              }}
            >
              <div
                style={{
                  padding: "25px 60px",
                  border: `3px solid ${COOKD_THEME.nothingWhite}`,
                  borderRadius: "16px",
                  fontSize: "36px",
                  fontWeight: 800,
                  display: "flex",
                  alignItems: "center",
                  gap: "15px",
                }}
              >
                GET IT ON GOOGLE PLAY
              </div>
            </div>

            {/* Final Referral Code Highlight */}
            <div
              style={{
                backgroundColor: COOKD_THEME.nothingSurface,
                border: `1px solid ${COOKD_THEME.neonRed}`,
                padding: "40px 60px",
                borderRadius: "24px",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontSize: "28px",
                  color: COOKD_THEME.neonRed,
                  fontWeight: 700,
                  marginBottom: "15px",
                }}
              >
                UNLOCK 5 FREE GENERATIONS
              </div>
              <div style={{ fontSize: "48px", fontWeight: 800 }}>
                CODE:{" "}
                <span style={{ color: COOKD_THEME.nothingWhite }}>
                  COOKD100
                </span>
              </div>
            </div>
          </AbsoluteFill>
        );
      })()}
    </AbsoluteFill>
  );
};
