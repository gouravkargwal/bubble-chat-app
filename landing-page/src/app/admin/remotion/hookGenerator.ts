// ── Dynamic hook text generator for Remotion videos ──
// Generates the first 2-second hook frame based on conversation data.
// No hardcoded arrays — pure logical templates.

interface HookInput {
  hookStyle?: string;
  personName?: string;
  messages?: { sender: string; text: string }[];
  winningLine?: string;
  strategyLabel?: string;
  timeGapMinutes?: number;
}

const STRATEGY_LABELS: Record<string, string> = {
  FRAME_CONTROL: "Frame Control",
  CHARM: "The Charm",
  PATTERN_INTERRUPT: "Pattern Interrupt",
  VISUAL_HOOK: "Visual Hook",
  CHALLENGE: "The Challenge",
  TARGET_LOCK: "Target Lock",
  PERSONA_SCAN: "Persona Scan",
  ANALYTICS: "Analytics",
  MEMORY_MODULE: "Memory Recall",
  SECURE: "Secure Mode",
  COOKD_AI: "Cookd AI",
};

function getLastUserMessage(
  messages?: { sender: string; text: string }[],
): string {
  if (!messages) return "";
  const userMsgs = messages.filter((m) => m.sender === "you");
  return userMsgs.length > 0 ? userMsgs[userMsgs.length - 1].text : "";
}

function getLastThemMessage(
  messages?: { sender: string; text: string }[],
): string {
  if (!messages) return "";
  const themMsgs = messages.filter((m) => m.sender === "them");
  return themMsgs.length > 0 ? themMsgs[themMsgs.length - 1].text : "";
}

function formatTimeGap(minutes?: number): string {
  if (!minutes || minutes <= 0) return "";
  if (minutes < 60) return `${minutes} minutes`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hours`;
  const days = Math.round(hours / 24);
  return `${days} days`;
}

export function generateHook(input: HookInput): string {
  const style = input.hookStyle || "strategy";
  const name = input.personName || "they";
  const userMsg = getLastUserMessage(input.messages);
  const themMsg = getLastThemMessage(input.messages);
  const winLine = input.winningLine || "";
  const strategyLabel =
    STRATEGY_LABELS[input.strategyLabel || ""] ||
    input.strategyLabel ||
    "Cookd AI";
  const gap = formatTimeGap(input.timeGapMinutes);

  switch (style) {
    case "roast": {
      // User's message was low-effort — roast it
      if (userMsg && userMsg.length < 15) {
        return `"${userMsg}" — really? Let me fix this.`;
      }
      if (themMsg) {
        return `She said "${themMsg.substring(0, 40)}" — his reply? Crickets.`;
      }
      return "99% of guys would send 'hey'. You're not 99%.";
    }

    case "gap": {
      // Time gap visible — she went cold
      if (gap) {
        return `${gap} of silence. One message changed it.`;
      }
      if (themMsg && themMsg.length < 10) {
        return `She left him on read. Then this happened.`;
      }
      return "She was losing interest. Watch this.";
    }

    case "outcome": {
      // Winning line sets up a date — show the result
      if (
        winLine.toLowerCase().includes("free") ||
        winLine.toLowerCase().includes("coffee") ||
        winLine.toLowerCase().includes("drink") ||
        winLine.toLowerCase().includes("meet") ||
        winLine.toLowerCase().includes("when") ||
        winLine.toLowerCase().includes("dinner")
      ) {
        return `He went from "hey" to "when are you free?" in one reply.`;
      }
      if (winLine.toLowerCase().includes("?") && winLine.length > 20) {
        return `One question. One date. Here's how.`;
      }
      return `Left on read → left on "yes".`;
    }

    case "strategy":
    default: {
      // Strategy-focused — showcase the AI's technique
      return `${strategyLabel}. That's all it took.`;
    }
  }
}
