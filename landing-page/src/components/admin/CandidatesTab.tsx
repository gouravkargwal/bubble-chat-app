"use client";

import type { VideoCandidate } from "./types";
import { HOOK_LABELS, HOOK_COLORS, ScoreBadge } from "./helpers";

export function CandidatesTab({
  candidates,
  selectedIds,
  loading,
  error,
  rendering,
  renderProgress,
  scoreBuckets,
  onToggleSelect,
  onSelectAll,
  onRenderSingle,
  onBatchRender,
}: {
  candidates: VideoCandidate[];
  selectedIds: Set<string>;
  loading: boolean;
  error: string | null;
  rendering: boolean;
  renderProgress: string | null;
  scoreBuckets: { high: number; medium: number };
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onRenderSingle: (c: VideoCandidate) => void;
  onBatchRender: () => void;
}) {
  const renderableCount = scoreBuckets.high + scoreBuckets.medium;

  if (!loading && candidates.length === 0 && !error) {
    return (
      <div className="text-center py-24">
        <p className="text-lg font-bold">No candidates found</p>
        <p className="text-sm text-[rgba(255,255,255,0.45)] mt-2">
          Make sure the backend has interactions with transcripts.
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total", value: candidates.length, color: "" },
          {
            label: "Renderable",
            value: renderableCount,
            color: "text-[#00FF66]",
          },
          {
            label: "🔥 Viral",
            value: scoreBuckets.high,
            color: "text-[#FF003C]",
          },
          {
            label: "Selected",
            value: selectedIds.size,
            color: "text-[#2563EB]",
          },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a] p-4"
          >
            <div className="text-[10px] font-mono text-[rgba(255,255,255,0.3)] tracking-wider uppercase">
              {s.label}
            </div>
            <div className={`text-2xl font-extrabold mt-1 ${s.color}`}>
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* Action bar */}
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onSelectAll}
            className="text-xs font-mono text-[rgba(255,255,255,0.45)] hover:text-white transition-colors"
          >
            {selectedIds.size === candidates.length
              ? "Deselect All"
              : "Select All"}
          </button>
        </div>
        <div className="flex items-center gap-3">
          {renderProgress && (
            <span className="text-xs font-mono text-[rgba(255,255,255,0.7)]">
              {renderProgress}
            </span>
          )}
          <button
            onClick={onBatchRender}
            disabled={selectedIds.size === 0 || rendering}
            className={`px-6 py-2 rounded-full text-xs font-bold transition-all duration-200 ${
              selectedIds.size === 0 || rendering
                ? "bg-[rgba(255,255,255,0.05)] text-[rgba(255,255,255,0.3)] cursor-not-allowed"
                : "bg-[#FF003C] text-white hover:shadow-[0_0_20px_rgba(255,0,60,0.25)]"
            }`}
          >
            {rendering
              ? "Processing..."
              : `🎬 Render ${selectedIds.size} videos`}
          </button>
        </div>
      </div>

      {/* Candidate list */}
      {!loading && (
        <div className="space-y-3">
          {candidates.map((c) => {
            const sel = selectedIds.has(c.id);
            return (
              <div
                key={c.id}
                className={`rounded-xl border transition-all duration-200 ${
                  sel
                    ? "border-[#FF003C] bg-[#FF003C]/5"
                    : "border-[rgba(255,255,255,0.1)] bg-[#0a0a0a]"
                }`}
              >
                <div className="p-4 sm:p-5">
                  <div className="flex items-start gap-4">
                    {/* Checkbox */}
                    <div
                      className={`flex-shrink-0 w-5 h-5 rounded border-2 mt-0.5 flex items-center justify-center transition-colors cursor-pointer ${
                        sel
                          ? "border-[#FF003C] bg-[#FF003C]"
                          : "border-[rgba(255,255,255,0.2)]"
                      }`}
                      onClick={() => onToggleSelect(c.id)}
                    >
                      {sel && (
                        <svg
                          className="h-3 w-3 text-white"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={3}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M4.5 12.75l6 6 9-13.5"
                          />
                        </svg>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <span className="font-heading text-base font-bold">
                          {c.personName}
                        </span>
                        <span
                          className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border"
                          style={{
                            color: HOOK_COLORS[c.hookStyle],
                            borderColor: HOOK_COLORS[c.hookStyle],
                          }}
                        >
                          {HOOK_LABELS[c.hookStyle] || c.hookStyle}
                        </span>
                        <ScoreBadge score={c.viralScore} />
                        <span className="text-xs text-[rgba(255,255,255,0.3)]">
                          {c.strategyLabel}
                        </span>
                      </div>

                      <p className="text-sm text-[rgba(255,255,255,0.7)] italic mb-2">
                        &ldquo;{c.winningLine}&rdquo;
                      </p>

                      <div className="flex items-center gap-2 mt-3">
                        <button
                          onClick={() => onRenderSingle(c)}
                          disabled={rendering}
                          className="px-4 py-1.5 text-xs font-bold rounded-full bg-[#FF003C] text-white hover:shadow-[0_0_15px_rgba(255,0,60,0.2)] transition-all disabled:opacity-30"
                        >
                          🎬 Render
                        </button>
                      </div>

                      <details className="group mt-2">
                        <summary className="text-[10px] font-mono text-[rgba(255,255,255,0.3)] cursor-pointer hover:text-white transition-colors">
                          Chat ({c.transcript.length} messages)
                        </summary>
                        <div className="mt-2 space-y-1.5">
                          {c.transcript.slice(0, 10).map((m, i) => (
                            <div
                              key={i}
                              className={`flex ${
                                m.sender === "you"
                                  ? "justify-end"
                                  : "justify-start"
                              }`}
                            >
                              <div
                                className={`max-w-[80%] rounded-lg px-3 py-1.5 text-xs ${
                                  m.sender === "you"
                                    ? "bg-[#FF003C]/20 border border-[#FF003C]/30 text-white"
                                    : "bg-[#0a0a0a] border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.7)]"
                                }`}
                              >
                                {m.text}
                              </div>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
