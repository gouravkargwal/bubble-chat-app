"use client";

import { useState } from "react";
import type { RenderedVideo, RenderedFilters } from "./types";
import { HOOK_LABELS, HOOK_COLORS, ScoreBadge, formatBytes } from "./helpers";
import { DEFAULT_FILTERS } from "./helpers";
import { PostWizard } from "./PostWizard";

export function RenderedTab({
  videos,
  loading,
  error,
  appliedFilters,
  onDelete,
  onPublished,
}: {
  videos: RenderedVideo[];
  loading: boolean;
  error: string | null;
  appliedFilters: RenderedFilters;
  onDelete: (id: string, personName: string) => void;
  onPublished: () => void;
}) {
  const [postVideo, setPostVideo] = useState<RenderedVideo | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!loading && videos.length === 0 && !error) {
    return (
      <div className="text-center py-24">
        <p className="text-lg font-bold">No rendered videos found</p>
        <p className="text-sm text-[rgba(255,255,255,0.45)] mt-2">
          {appliedFilters === DEFAULT_FILTERS
            ? "Render some candidates first."
            : "Try adjusting your filters."}
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {videos.map((v) => (
          <div
            key={v.id}
            className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a]"
          >
            <div className="p-4 sm:p-5">
              <div className="flex items-start gap-4">
                {/* Status indicator + Score badge */}
                <div className="flex flex-col items-center gap-2 flex-shrink-0">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      v.status === "completed"
                        ? "bg-[#00FF66]"
                        : v.status === "failed"
                        ? "bg-[#FF003C]"
                        : "bg-[#FF8C00]"
                    }`}
                  />
                  <ScoreBadge score={v.viralScore} />
                </div>

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

                  {/* Video preview toggle */}
                  {v.status === "completed" && (
                    <>
                      <button
                        onClick={() =>
                          setExpandedId(expandedId === v.id ? null : v.id)
                        }
                        className="text-xs text-[rgba(255,255,255,0.45)] hover:text-white transition-colors mb-2"
                      >
                        {expandedId === v.id
                          ? "▲ Hide preview"
                          : "▼ Show preview"}
                      </button>
                      {expandedId === v.id && (
                        <video
                          src={`/api/stream-video/${v.id}`}
                          controls
                          className="w-full rounded-lg mb-3 max-h-[400px] object-contain bg-black"
                          preload="auto"
                        />
                      )}
                    </>
                  )}

                  <div className="flex items-center gap-2 mt-3 flex-wrap">
                    <a
                      href={`/api/admin/rendered-videos/${v.id}/download`}
                      className="px-4 py-1.5 text-xs font-bold rounded-full bg-[#FF003C] text-white hover:shadow-[0_0_15px_rgba(255,0,60,0.2)] transition-all"
                      download
                    >
                      ⬇ Download
                    </a>
                    {v.status === "completed" && (
                      <button
                        onClick={() => setPostVideo(v)}
                        className="px-4 py-1.5 text-xs font-bold rounded-full bg-[#00FF66] text-black hover:shadow-[0_0_15px_rgba(0,255,102,0.2)] transition-all"
                      >
                        🚀 Post
                      </button>
                    )}
                    <button
                      onClick={() => onDelete(v.id, v.personName)}
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

      {/* Post Wizard Modal */}
      {postVideo && (
        <PostWizard
          video={postVideo}
          onClose={() => setPostVideo(null)}
          onPublished={() => {
            setPostVideo(null);
            onPublished();
          }}
        />
      )}
    </>
  );
}
