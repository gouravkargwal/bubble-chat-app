"use client";

import { useState, useEffect } from "react";
import type { PublishedVideo } from "./types";

export function PublishedTab() {
  const [videos, setVideos] = useState<PublishedVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPublished = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/publish/history?limit=50");
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setVideos(data.published || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPublished();
  }, []);

  if (!loading && videos.length === 0 && !error) {
    return (
      <div className="text-center py-24">
        <p className="text-lg font-bold">No videos published yet</p>
        <p className="text-sm text-[rgba(255,255,255,0.45)] mt-2">
          Render a video, then use the Post button to publish.
        </p>
      </div>
    );
  }

  const platformIcon: Record<string, string> = {
    instagram: "📸",
    youtube: "▶️",
  };

  const platformLabel: Record<string, string> = {
    instagram: "Instagram Reels",
    youtube: "YouTube Shorts",
  };

  return (
    <div className="space-y-3">
      {error && (
        <div className="rounded-xl border border-[#FF003C]/30 bg-[#FF003C]/10 p-3 mb-4">
          <p className="text-sm text-[#FF003C] font-mono">{error}</p>
        </div>
      )}

      {videos.map((v) => (
        <div
          key={v.id}
          className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a]"
        >
          <div className="p-4 sm:p-5">
            <div className="flex items-start gap-4">
              {/* Platform icon */}
              <div className="flex flex-col items-center gap-1 flex-shrink-0 w-10">
                <span className="text-2xl">
                  {platformIcon[v.platform] || "🌐"}
                </span>
                <div
                  className={`w-2 h-2 rounded-full ${
                    v.status === "posted"
                      ? "bg-[#00FF66]"
                      : v.status === "failed"
                      ? "bg-[#FF003C]"
                      : "bg-[#FF8C00]"
                  }`}
                />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1 flex-wrap">
                  <span className="font-heading text-sm font-bold">
                    {platformLabel[v.platform] || v.platform}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                      v.status === "posted"
                        ? "bg-[#00FF66]/10 text-[#00FF66]"
                        : v.status === "failed"
                        ? "bg-[#FF003C]/10 text-[#FF003C]"
                        : "bg-[#FF8C00]/10 text-[#FF8C00]"
                    }`}
                  >
                    {v.status}
                  </span>
                </div>

                {v.audioTrackTitle && (
                  <p className="text-xs text-[rgba(255,255,255,0.45)] mb-1">
                    🎵 {v.audioTrackTitle}
                  </p>
                )}

                {v.caption && (
                  <p className="text-sm text-[rgba(255,255,255,0.7)] italic mb-2 line-clamp-2">
                    {v.caption}
                  </p>
                )}

                <div className="flex items-center gap-4 mt-2 text-xs text-[rgba(255,255,255,0.45)]">
                  <span>👁️ {v.viewCount}</span>
                  <span>❤️ {v.likeCount}</span>
                  <span>💬 {v.commentCount}</span>
                  <span>{new Date(v.createdAt).toLocaleDateString()}</span>
                </div>

                <div className="flex items-center gap-2 mt-3">
                  {v.platformUrl && (
                    <a
                      href={v.platformUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1 text-xs font-bold rounded-full bg-[#FF003C] text-white hover:shadow-[0_0_15px_rgba(255,0,60,0.2)] transition-all"
                    >
                      🔗 View Post
                    </a>
                  )}
                  {v.errorMessage && (
                    <span className="text-[10px] text-[#FF003C] font-mono">
                      {v.errorMessage}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
