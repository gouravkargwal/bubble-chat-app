import type { RenderedFilters, CandidateFilters } from "./types";

// ── Hook Style Constants ──

export const HOOK_LABELS: Record<string, string> = {
  roast: "🔥 Roast",
  gap: "⏰ Time Gap",
  outcome: "🎯 Outcome",
  strategy: "🧠 Strategy",
  bet: "🎲 Bet",
  clapback: "👏 Clapback",
  identity: "🪞 Identity",
  social: "📈 Social Proof",
  slams: "💥 Slam",
};

export const HOOK_STYLES = Object.keys(HOOK_LABELS);

export const HOOK_COLORS: Record<string, string> = {
  roast: "#FF003C",
  gap: "#FF8C00",
  outcome: "#00FF66",
  strategy: "#2563EB",
  bet: "#FFFFFF",
  clapback: "#FFD700",
  identity: "#8B5CF6",
  social: "#00C9FF",
  slams: "#FF6B35",
};

export const STATUS_OPTIONS = [
  "",
  "completed",
  "failed",
  "queued",
  "rendering",
];

export const DEFAULT_FILTERS: RenderedFilters = {
  search: "",
  status: "",
  hookStyle: "",
  strategyLabel: "",
  minScore: "",
  maxScore: "",
};

export const DEFAULT_CANDIDATE_FILTERS: CandidateFilters = {
  search: "",
  hookType: "",
  priority: "",
  minScore: "",
  maxScore: "",
};

const PRIORITY_OPTIONS = ["", "high", "medium", "low"];
const HOOK_TYPE_OPTIONS = ["", ...HOOK_STYLES];

// ── Components ──

export function ScoreBadge({ score }: { score: number }) {
  if (score >= 50)
    return <span className="text-[#FF003C] font-extrabold">🔥 {score}</span>;
  if (score >= 30)
    return <span className="text-[#00FF66] font-bold">✅ {score}</span>;
  return <span className="text-[rgba(255,255,255,0.3)]">{score}</span>;
}

// Shows whether hookStyle/viralScore came from the vision LLM's own
// classification or the message-heuristic fallback (used for interactions
// saved before the LLM fields existed).
export function SourceBadge({ source }: { source?: "llm" | "heuristic" }) {
  if (source === "llm") {
    return (
      <span
        className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border"
        style={{ color: "#8B5CF6", borderColor: "#8B5CF6" }}
        title="Scored by the vision LLM's own classification"
      >
        LLM
      </span>
    );
  }
  return (
    <span
      className="text-[9px] font-mono px-1.5 py-0.5 rounded border"
      style={{
        color: "rgba(255,255,255,0.35)",
        borderColor: "rgba(255,255,255,0.15)",
      }}
      title="Scored by the message-length heuristic (no LLM classification on this row)"
    >
      HEURISTIC
    </span>
  );
}

// ── Utils ──

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}
