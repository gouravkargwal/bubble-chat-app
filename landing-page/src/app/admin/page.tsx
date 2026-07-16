"use client";

import { useState, useEffect, useCallback } from "react";
import type {
  VideoCandidate,
  RenderedVideo,
  RenderedFilters,
  CandidateFilters,
} from "@/components/admin/types";
import {
  DEFAULT_FILTERS,
  DEFAULT_CANDIDATE_FILTERS,
} from "@/components/admin/helpers";
import { FilterBar } from "@/components/admin/FilterBar";
import { CandidateFilterBar } from "@/components/admin/CandidateFilterBar";
import { PaginationBar } from "@/components/admin/PaginationBar";
import { CandidatesTab } from "@/components/admin/CandidatesTab";
import { RenderedTab } from "@/components/admin/RenderedTab";

const PAGE_SIZE = 20;

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

  // ── Rendered videos pagination & filters ──
  const [renderedPage, setRenderedPage] = useState(1);
  const [renderedTotal, setRenderedTotal] = useState(0);
  const [renderedTotalPages, setRenderedTotalPages] = useState(1);
  const [filters, setFilters] = useState<RenderedFilters>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] =
    useState<RenderedFilters>(DEFAULT_FILTERS);

  // ── Candidates pagination & filters ──
  const [candidatePage, setCandidatePage] = useState(1);
  const [candidateTotal, setCandidateTotal] = useState(0);
  const [candidateTotalPages, setCandidateTotalPages] = useState(1);
  const [candidateFilters, setCandidateFilters] = useState<CandidateFilters>(
    DEFAULT_CANDIDATE_FILTERS
  );
  const [appliedCandidateFilters, setAppliedCandidateFilters] =
    useState<CandidateFilters>(DEFAULT_CANDIDATE_FILTERS);
  const [candidateBuckets, setCandidateBuckets] = useState({
    high: 0,
    medium: 0,
  });

  const fetchCandidates = useCallback(
    async (page: number, filtersToApply: CandidateFilters) => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.set("page", String(page));
        params.set("pageSize", String(PAGE_SIZE));
        if (filtersToApply.search) params.set("search", filtersToApply.search);
        if (filtersToApply.hookType)
          params.set("hookType", filtersToApply.hookType);
        if (filtersToApply.priority)
          params.set("priority", filtersToApply.priority);
        if (filtersToApply.minScore)
          params.set("minScore", filtersToApply.minScore);
        if (filtersToApply.maxScore)
          params.set("maxScore", filtersToApply.maxScore);

        const res = await fetch(
          `/api/admin/video-pipeline/candidates?${params.toString()}`
        );
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        const data = await res.json();
        setCandidates(data.candidates || []);
        setCandidateTotal(data.total);
        setCandidateTotalPages(data.totalPages);
        setCandidatePage(data.page);
        setCandidateBuckets(data.score_buckets || { high: 0, medium: 0 });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const fetchRenderedVideos = useCallback(
    async (page: number, filtersToApply: RenderedFilters) => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.set("page", String(page));
        params.set("pageSize", String(PAGE_SIZE));
        if (filtersToApply.search) params.set("search", filtersToApply.search);
        if (filtersToApply.status) params.set("status", filtersToApply.status);
        if (filtersToApply.hookStyle)
          params.set("hookStyle", filtersToApply.hookStyle);
        if (filtersToApply.strategyLabel)
          params.set("strategyLabel", filtersToApply.strategyLabel);
        if (filtersToApply.minScore)
          params.set("minScore", filtersToApply.minScore);
        if (filtersToApply.maxScore)
          params.set("maxScore", filtersToApply.maxScore);

        const res = await fetch(
          `/api/admin/rendered-videos?${params.toString()}`
        );
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        const data = await res.json();
        setRenderedVideos(data.videos || []);
        setRenderedTotal(data.total);
        setRenderedTotalPages(data.totalPages);
        setRenderedPage(data.page);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchCandidates(1, DEFAULT_CANDIDATE_FILTERS);
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
          isOpener: candidate.isOpener,
          keyDetail: candidate.keyDetail,
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

      const a = document.createElement("a");
      a.href = url;
      a.download = `cookd-${candidate.personName
        .toLowerCase()
        .replace(/\s+/g, "-")}.mp4`;
      a.click();
      URL.revokeObjectURL(url);

      fetchRenderedVideos(renderedPage, appliedFilters);
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
            isOpener: candidate.isOpener,
            keyDetail: candidate.keyDetail,
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
    fetchRenderedVideos(renderedPage, appliedFilters);

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
      fetchRenderedVideos(renderedPage, appliedFilters);
    } catch (err) {
      setRenderLog((prev) => [
        `❌ Failed to delete ${personName}: ${
          err instanceof Error ? err.message : "unknown error"
        }`,
        ...prev,
      ]);
    }
  };

  const applyFilters = () => {
    setAppliedFilters({ ...filters });
    fetchRenderedVideos(1, filters);
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setAppliedFilters(DEFAULT_FILTERS);
    fetchRenderedVideos(1, DEFAULT_FILTERS);
  };

  const goToPage = (p: number) => {
    if (p < 1 || p > renderedTotalPages) return;
    fetchRenderedVideos(p, appliedFilters);
  };

  // ── Candidate filter handlers ──
  const applyCandidateFilters = () => {
    setAppliedCandidateFilters({ ...candidateFilters });
    fetchCandidates(1, candidateFilters);
  };

  const resetCandidateFilters = () => {
    setCandidateFilters(DEFAULT_CANDIDATE_FILTERS);
    setAppliedCandidateFilters(DEFAULT_CANDIDATE_FILTERS);
    fetchCandidates(1, DEFAULT_CANDIDATE_FILTERS);
  };

  const goToCandidatePage = (p: number) => {
    if (p < 1 || p > candidateTotalPages) return;
    fetchCandidates(p, appliedCandidateFilters);
  };

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
              onClick={() => {
                if (tab === "candidates")
                  fetchCandidates(candidatePage, appliedCandidateFilters);
                else fetchRenderedVideos(renderedPage, appliedFilters);
              }}
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
              fetchRenderedVideos(1, appliedFilters);
            }}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
              tab === "rendered"
                ? "bg-[#FF003C] text-white"
                : "text-[rgba(255,255,255,0.45)] hover:text-white"
            }`}
          >
            ✅ Rendered ({renderedTotal})
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-[#FF003C]/30 bg-[#FF003C]/10 p-4">
            <p className="text-sm text-[#FF003C] font-mono">Error: {error}</p>
            <button
              onClick={() => {
                if (tab === "candidates")
                  fetchCandidates(candidatePage, appliedCandidateFilters);
                else fetchRenderedVideos(renderedPage, appliedFilters);
              }}
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
        {tab === "candidates" && (
          <>
            <CandidateFilterBar
              filters={candidateFilters}
              onChange={setCandidateFilters}
              onApply={applyCandidateFilters}
              onReset={resetCandidateFilters}
            />

            <CandidatesTab
              candidates={candidates}
              selectedIds={selectedIds}
              loading={loading}
              error={error}
              rendering={rendering}
              renderProgress={renderProgress}
              scoreBuckets={candidateBuckets}
              onToggleSelect={toggleSelect}
              onSelectAll={selectAll}
              onRenderSingle={handleRender}
              onBatchRender={handleBatchRender}
            />

            <PaginationBar
              page={candidatePage}
              totalPages={candidateTotalPages}
              total={candidateTotal}
              onPageChange={goToCandidatePage}
            />
          </>
        )}

        {/* ── RENDERED VIDEOS TAB ── */}
        {tab === "rendered" && (
          <>
            <FilterBar
              filters={filters}
              onChange={setFilters}
              onApply={applyFilters}
              onReset={resetFilters}
            />

            <RenderedTab
              videos={renderedVideos}
              loading={loading}
              error={error}
              appliedFilters={appliedFilters}
              onDelete={handleDeleteVideo}
            />

            <PaginationBar
              page={renderedPage}
              totalPages={renderedTotalPages}
              total={renderedTotal}
              onPageChange={goToPage}
            />
          </>
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
