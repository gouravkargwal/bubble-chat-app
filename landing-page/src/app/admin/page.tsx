"use client";

import { useState, useEffect, useCallback } from "react";

// ── Types ──

interface TranscriptMessage {
  sender: "them" | "you";
  text: string;
}

interface VideoCandidate {
  id: string;
  personName: string;
  detectedApp: string;
  strategyLabel: string;
  winningLine: string;
  coachReasoning: string;
  theirLastMessage: string;
  transcript: TranscriptMessage[];
  hookStyle: string;
  viralScore: number;
  priority: string;
  createdAt: string;
}

interface RenderedVideo {
  id: string;
  interactionId: string | null;
  personName: string;
  winningLine: string;
  strategyLabel: string;
  hookStyle: string;
  viralScore: number;
  fileSizeBytes: number;
  status: string;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

// ── Helpers ──

const HOOK_LABELS: Record<string, string> = {
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

const HOOK_COLORS: Record<string, string> = {
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

function ScoreBadge({ score }: { score: number }) {
  if (score >= 50)
    return <span className="text-[#FF003C] font-extrabold">🔥 {score}</span>;
  if (score >= 30)
    return <span className="text-[#00FF66] font-bold">✅ {score}</span>;
  return <span className="text-[rgba(255,255,255,0.3)]">{score}</span>;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

// ── Main Page ──

export default function AdminVideoPipeline() {
  const [candidates, setCandidates] = useState<VideoCandidate[]>([]);
  const [renderedVideos, setRenderedVideos] = useState<RenderedVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [rendering, setRendering] = useState(false);
  const [renderLog, setRenderLog] = useState<string[]>([]);
  const [renderProgress, setRenderProgress] = useState<string | null>(null);
  const [tab, setTab] = useState<"candidates" | "rendered">("candidates");

  const fetchCandidates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/video-pipeline/candidates?limit=50");
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      setCandidates(data.candidates || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRenderedVideos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/rendered-videos?limit=100");
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      setRenderedVideos(data.videos || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === candidates.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(candidates.map((c) => c.id)));
    }
  };

  const handleRender = async (candidate: VideoCandidate) => {
    if (rendering) return;
    setRendering(true);
    setRenderProgress(`Rendering ${candidate.personName}...`);

    try {
      const res = await fetch("/api/render-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          personName: candidate.personName,
          messages: candidate.transcript,
          winningLine: candidate.winningLine,
          strategyLabel: candidate.strategyLabel,
          hookStyle: candidate.hookStyle,
          viralScore: candidate.viralScore,
          interactionId: candidate.id,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || `Render failed (${res.status})`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      setRenderLog((prev) => [
        `🎬 ${candidate.personName} — rendered (${(
          blob.size /
          1024 /
          1024
        ).toFixed(1)} MB)`,
        ...prev,
      ]);

      // Trigger download automatically
      const a = document.createElement("a");
      a.href = url;
      a.download = `cookd-${candidate.personName
        .toLowerCase()
        .replace(/\s+/g, "-")}.mp4`;
      a.click();
      URL.revokeObjectURL(url);

      // Refresh rendered list
      fetchRenderedVideos();
    } catch (err) {
      setRenderLog((prev) => [
        `❌ ${candidate.personName}: ${
          err instanceof Error ? err.message : "unknown error"
        }`,
        ...prev,
      ]);
    } finally {
      setRendering(false);
      setRenderProgress(null);
    }
  };

  const handleBatchRender = async () => {
    if (selectedIds.size === 0 || rendering) return;
    setRendering(true);
    const ids = Array.from(selectedIds);
    setRenderProgress(`Rendering ${ids.length} videos...`);

    let success = 0;
    let failed = 0;

    for (const id of ids) {
      const candidate = candidates.find((c) => c.id === id);
      if (!candidate) continue;

      try {
        const res = await fetch("/api/render-video", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            personName: candidate.personName,
            messages: candidate.transcript,
            winningLine: candidate.winningLine,
            strategyLabel: candidate.strategyLabel,
            hookStyle: candidate.hookStyle,
            viralScore: candidate.viralScore,
            interactionId: candidate.id,
          }),
        });

        if (!res.ok) {
          failed++;
          setRenderLog((prev) => [
            `❌ ${candidate.personName}: render failed (${res.status})`,
            ...prev,
          ]);
          continue;
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        // Trigger download
        const a = document.createElement("a");
        a.href = url;
        a.download = `cookd-${candidate.personName
          .toLowerCase()
          .replace(/\s+/g, "-")}.mp4`;
        a.click();
        URL.revokeObjectURL(url);

        setRenderLog((prev) => [
          `🎬 ${candidate.personName} — rendered (${(
            blob.size /
            1024 /
            1024
          ).toFixed(1)} MB)`,
          ...prev,
        ]);
        success++;
      } catch (err) {
        failed++;
        setRenderLog((prev) => [
          `❌ ${candidate.personName}: ${
            err instanceof Error ? err.message : "unknown error"
          }`,
          ...prev,
        ]);
      }
    }

    setRenderProgress(null);
    setRendering(false);
    fetchRenderedVideos();

    setRenderLog((prev) => [
      `📊 Batch done: ${success} succeeded, ${failed} failed`,
      ...prev,
    ]);
  };

  const handleDeleteVideo = async (videoId: string, personName: string) => {
    try {
      const res = await fetch(`/api/admin/rendered-videos/${videoId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(`Delete returned ${res.status}`);
      setRenderedVideos((prev) => prev.filter((v) => v.id !== videoId));
      setRenderLog((prev) => [`🗑️ Deleted video for ${personName}`, ...prev]);
    } catch (err) {
      setRenderLog((prev) => [
        `❌ Failed to delete ${personName}: ${
          err instanceof Error ? err.message : "unknown error"
        }`,
        ...prev,
      ]);
    }
  };

  const renderableCount = candidates.filter((c) => c.viralScore >= 30).length;
  const highCount = candidates.filter((c) => c.viralScore >= 50).length;

  return (
    <main className="min-h-screen pt-24 pb-16 px-4 sm:px-6 bg-black text-white">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-extrabold tracking-tight">
              🎬 Video Pipeline
            </h1>
            <p className="text-sm text-[rgba(255,255,255,0.45)] mt-1">
              Select candidates. Click Render. Videos save permanently.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={
                tab === "candidates" ? fetchCandidates : fetchRenderedVideos
              }
              className="px-4 py-2 text-xs font-bold border border-[rgba(255,255,255,0.1)] rounded-full hover:bg-white/5 transition-colors"
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a] p-1 w-fit">
          <button
            onClick={() => setTab("candidates")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
              tab === "candidates"
                ? "bg-[#FF003C] text-white"
                : "text-[rgba(255,255,255,0.45)] hover:text-white"
            }`}
          >
            📋 Candidates ({candidates.length})
          </button>
          <button
            onClick={() => {
              setTab("rendered");
              fetchRenderedVideos();
            }}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
              tab === "rendered"
                ? "bg-[#FF003C] text-white"
                : "text-[rgba(255,255,255,0.45)] hover:text-white"
            }`}
          >
            ✅ Rendered ({renderedVideos.length})
          </button>
        </div>

        {/* Stats */}
        {tab === "candidates" && (
          <div className="grid grid-cols-4 gap-3 mb-6">
            {[
              { label: "Total", value: candidates.length, color: "" },
              {
                label: "Renderable",
                value: renderableCount,
                color: "text-[#00FF66]",
              },
              { label: "🔥 Viral", value: highCount, color: "text-[#FF003C]" },
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
        )}

        {/* Action bar (candidates) */}
        {tab === "candidates" && (
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={selectAll}
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
                onClick={handleBatchRender}
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
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-[#FF003C]/30 bg-[#FF003C]/10 p-4">
            <p className="text-sm text-[#FF003C] font-mono">Error: {error}</p>
            <button
              onClick={
                tab === "candidates" ? fetchCandidates : fetchRenderedVideos
              }
              className="mt-2 text-xs font-mono text-[rgba(255,255,255,0.45)] underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-24">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 rounded-full border-2 border-[#FF003C] border-t-transparent animate-spin" />
              <p className="text-xs font-mono text-[rgba(255,255,255,0.45)]">
                Loading...
              </p>
            </div>
          </div>
        )}

        {/* ── CANDIDATES TAB ── */}
        {!loading &&
          tab === "candidates" &&
          candidates.length === 0 &&
          !error && (
            <div className="text-center py-24">
              <p className="text-lg font-bold">No candidates found</p>
              <p className="text-sm text-[rgba(255,255,255,0.45)] mt-2">
                Make sure the backend has interactions with transcripts.
              </p>
            </div>
          )}

        {!loading && tab === "candidates" && (
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
                        onClick={() => toggleSelect(c.id)}
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

                        {/* Render button */}
                        <div className="flex items-center gap-2 mt-3">
                          <button
                            onClick={() => handleRender(c)}
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

        {/* ── RENDERED VIDEOS TAB ── */}
        {!loading &&
          tab === "rendered" &&
          renderedVideos.length === 0 &&
          !error && (
            <div className="text-center py-24">
              <p className="text-lg font-bold">No rendered videos yet</p>
              <p className="text-sm text-[rgba(255,255,255,0.45)] mt-2">
                Render some candidates first.
              </p>
            </div>
          )}

        {!loading && tab === "rendered" && (
          <div className="space-y-3">
            {renderedVideos.map((v) => (
              <div
                key={v.id}
                className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a]"
              >
                <div className="p-4 sm:p-5">
                  <div className="flex items-start gap-4">
                    {/* Status indicator */}
                    <div
                      className={`flex-shrink-0 w-3 h-3 rounded-full mt-1.5 ${
                        v.status === "completed"
                          ? "bg-[#00FF66]"
                          : v.status === "failed"
                          ? "bg-[#FF003C]"
                          : "bg-[#FF8C00]"
                      }`}
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <span className="font-heading text-base font-bold">
                          {v.personName}
                        </span>
                        <span
                          className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border"
                          style={{
                            color: HOOK_COLORS[v.hookStyle],
                            borderColor: HOOK_COLORS[v.hookStyle],
                          }}
                        >
                          {HOOK_LABELS[v.hookStyle] || v.hookStyle}
                        </span>
                        <span className="text-xs font-mono text-[rgba(255,255,255,0.3)]">
                          {formatBytes(v.fileSizeBytes)}
                        </span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                            v.status === "completed"
                              ? "bg-[#00FF66]/10 text-[#00FF66]"
                              : v.status === "failed"
                              ? "bg-[#FF003C]/10 text-[#FF003C]"
                              : "bg-[#FF8C00]/10 text-[#FF8C00]"
                          }`}
                        >
                          {v.status}
                        </span>
                      </div>

                      <p className="text-sm text-[rgba(255,255,255,0.7)] italic mb-2">
                        &ldquo;{v.winningLine}&rdquo;
                      </p>

                      <div className="flex items-center gap-2 mt-3">
                        <a
                          href={`/api/admin/rendered-videos/${v.id}/download`}
                          className="px-4 py-1.5 text-xs font-bold rounded-full bg-[#FF003C] text-white hover:shadow-[0_0_15px_rgba(255,0,60,0.2)] transition-all"
                          download
                        >
                          ⬇ Download
                        </a>
                        <button
                          onClick={() => handleDeleteVideo(v.id, v.personName)}
                          className="px-4 py-1.5 text-xs font-bold rounded-full border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-[#FF003C] hover:border-[#FF003C] transition-all"
                        >
                          🗑 Delete
                        </button>
                        <span className="text-[10px] font-mono text-[rgba(255,255,255,0.25)]">
                          {new Date(v.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Render Log */}
        {renderLog.length > 0 && (
          <div className="mt-8">
            <h2 className="font-heading text-sm font-bold mb-3 text-[rgba(255,255,255,0.45)] uppercase tracking-wider">
              Log
            </h2>
            <div className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a] p-4 max-h-48 overflow-y-auto">
              {renderLog.map((entry, i) => (
                <p
                  key={i}
                  className="text-xs font-mono text-[rgba(255,255,255,0.5)] mb-1"
                >
                  {entry}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Architecture note */}
        <div className="mt-8 rounded-xl border border-[rgba(255,255,255,0.08)] bg-[#0a0a0a]/50 p-4">
          <p className="text-[10px] font-mono text-[rgba(255,255,255,0.25)] leading-relaxed">
            Admin API calls go through a Clerk-authenticated BFF proxy (
            <code className="text-[#FF003C]">/api/admin/*</code>) that forwards
            to the backend with an internal admin key. Rendered videos are saved
            to <code className="text-[#00FF66]">./rendered-videos/</code> and
            tracked in the{" "}
            <code className="text-[#00FF66]">rendered_videos</code> DB table.
          </p>
        </div>
      </div>
    </main>
  );
}
