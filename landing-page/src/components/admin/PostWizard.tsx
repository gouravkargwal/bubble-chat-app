"use client";

import { useState, useEffect } from "react";
import type { RenderedVideo, TrendingTrack, PublishResult } from "./types";

interface PostWizardProps {
  video: RenderedVideo;
  onClose: () => void;
  onPublished: () => void;
}

export function PostWizard({ video, onClose, onPublished }: PostWizardProps) {
  const [tracks, setTracks] = useState<TrendingTrack[]>([]);
  const [selectedTrack, setSelectedTrack] = useState<TrendingTrack | null>(
    null
  );
  const [previewTrackId, setPreviewTrackId] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [generatingCaption, setGeneratingCaption] = useState(false);
  const [platforms, setPlatforms] = useState({
    instagram: true,
    youtube: true,
  });
  const [publishing, setPublishing] = useState(false);
  const [results, setResults] = useState<PublishResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingTracks, setLoadingTracks] = useState(true);
  const [audioSearch, setAudioSearch] = useState("");

  // Fetch trending audio on mount
  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/admin/publish/trending-audio");
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        const data = await res.json();
        setTracks(data.tracks || []);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load audio tracks"
        );
      } finally {
        setLoadingTracks(false);
      }
    }
    load();
  }, []);

  const generateCaption = async () => {
    setGeneratingCaption(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/publish/generate-caption", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: "",
          winningLine: video.winningLine,
        }),
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setCaption(data.caption || "");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate caption"
      );
    } finally {
      setGeneratingCaption(false);
    }
  };

  const publish = async () => {
    setPublishing(true);
    setError(null);
    const selectedPlatforms = Object.entries(platforms)
      .filter(([, v]) => v)
      .map(([k]) => k);

    if (selectedPlatforms.length === 0) {
      setError("Select at least one platform");
      setPublishing(false);
      return;
    }

    try {
      const res = await fetch("/api/admin/publish/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          renderedVideoId: video.id,
          youtubeAudioId: selectedTrack?.youtubeId || "",
          audioTitle: selectedTrack?.title || "",
          caption,
          platforms: selectedPlatforms,
        }),
      });

      if (!res.ok) {
        const errData = await res
          .json()
          .catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || `Publish failed (${res.status})`);
      }

      const data = await res.json();
      setResults(data.results || []);
      onPublished();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setPublishing(false);
    }
  };

  const filteredTracks = audioSearch
    ? tracks.filter(
        (t) =>
          t.title.toLowerCase().includes(audioSearch.toLowerCase()) ||
          t.channelName.toLowerCase().includes(audioSearch.toLowerCase())
      )
    : tracks;

  const formatViews = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return n.toString();
  };

  const allSuccess = results && results.every((r) => r.status === "posted");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a] shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[rgba(255,255,255,0.1)]">
          <h2 className="font-heading text-lg font-extrabold">
            🚀 Post to Social
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-[rgba(255,255,255,0.45)] hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Video Preview */}
          <div>
            <label className="text-xs font-mono text-[rgba(255,255,255,0.45)] uppercase tracking-wider mb-2 block">
              Preview
            </label>
            <video
              src={`/api/stream-video/${video.id}`}
              controls
              className="w-full rounded-xl max-h-[300px] object-contain bg-black"
            />
            <p className="text-sm mt-2 text-[rgba(255,255,255,0.7)]">
              <span className="font-bold text-white">{video.personName}</span>{" "}
              &mdash;{" "}
              <span className="italic">&ldquo;{video.winningLine}&rdquo;</span>
            </p>
          </div>

          {/* Trending Audio Picker */}
          <div>
            <label className="text-xs font-mono text-[rgba(255,255,255,0.45)] uppercase tracking-wider mb-2 block">
              🎵 Trending Audio
            </label>
            <input
              type="text"
              placeholder="Search tracks..."
              value={audioSearch}
              onChange={(e) => setAudioSearch(e.target.value)}
              className="w-full mb-2 px-3 py-2 rounded-lg border border-[rgba(255,255,255,0.1)] bg-black text-sm text-white placeholder-[rgba(255,255,255,0.3)] focus:outline-none focus:border-[#FF003C]"
            />
            <div className="max-h-[200px] overflow-y-auto rounded-xl border border-[rgba(255,255,255,0.1)] bg-black">
              {loadingTracks ? (
                <div className="flex items-center justify-center py-8">
                  <div className="h-5 w-5 rounded-full border-2 border-[#FF003C] border-t-transparent animate-spin" />
                </div>
              ) : filteredTracks.length === 0 ? (
                <p className="text-center py-8 text-sm text-[rgba(255,255,255,0.3)]">
                  No tracks found
                </p>
              ) : (
                filteredTracks.map((track) => (
                  <div
                    key={track.youtubeId}
                    className={`${
                      selectedTrack?.youtubeId === track.youtubeId
                        ? "bg-[#FF003C]/10"
                        : ""
                    }`}
                  >
                    <div className="flex items-center gap-1 px-3 py-1.5 transition-colors hover:bg-white/5">
                      <button
                        onClick={() =>
                          setPreviewTrackId(
                            previewTrackId === track.youtubeId
                              ? null
                              : track.youtubeId
                          )
                        }
                        className="text-base flex-shrink-0 hover:scale-110 transition-transform"
                        title="Preview audio"
                      >
                        {previewTrackId === track.youtubeId ? "⏹" : "▶️"}
                      </button>
                      <button
                        onClick={() =>
                          setSelectedTrack(
                            selectedTrack?.youtubeId === track.youtubeId
                              ? null
                              : track
                          )
                        }
                        className="flex-1 flex items-center gap-2 min-w-0 py-1"
                      >
                        <span className="text-base flex-shrink-0">
                          {selectedTrack?.youtubeId === track.youtubeId
                            ? "🔊"
                            : "🎵"}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white truncate">
                            {track.title}
                          </p>
                          <p className="text-xs text-[rgba(255,255,255,0.45)] truncate">
                            {track.channelName} &bull;{" "}
                            {formatViews(track.viewCount)} views
                            {track.durationSeconds
                              ? ` \u2022 ${track.durationSeconds}s`
                              : ""}
                          </p>
                        </div>
                      </button>
                    </div>
                    {/* YouTube embed for audio preview */}
                    {previewTrackId === track.youtubeId && (
                      <div className="px-3 pb-2">
                        <iframe
                          src={`https://www.youtube.com/embed/${track.youtubeId}?autoplay=1&controls=1`}
                          className="w-full rounded-lg"
                          height="80"
                          allow="autoplay; encrypted-media"
                          allowFullScreen
                          style={{ border: "none" }}
                        />
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
            {selectedTrack && (
              <p className="text-xs text-[#00FF66] mt-1">
                Selected: {selectedTrack.title}
              </p>
            )}
          </div>

          {/* Caption */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-mono text-[rgba(255,255,255,0.45)] uppercase tracking-wider">
                📝 Caption
              </label>
              <button
                onClick={generateCaption}
                disabled={generatingCaption}
                className="text-xs font-bold px-3 py-1 rounded-full bg-[#2563EB]/20 text-[#60A5FA] hover:bg-[#2563EB]/30 transition-colors disabled:opacity-50"
              >
                {generatingCaption ? "Generating..." : "✨ Auto-Generate"}
              </button>
            </div>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-[rgba(255,255,255,0.1)] bg-black text-sm text-white placeholder-[rgba(255,255,255,0.3)] focus:outline-none focus:border-[#FF003C] resize-none"
              placeholder="Write a caption or auto-generate one..."
            />
          </div>

          {/* Platform Selector */}
          <div>
            <label className="text-xs font-mono text-[rgba(255,255,255,0.45)] uppercase tracking-wider mb-2 block">
              📲 Post to
            </label>
            <div className="flex gap-3">
              {[
                { key: "instagram", label: "Instagram Reels", icon: "📸" },
                { key: "youtube", label: "YouTube Shorts", icon: "▶️" },
              ].map((p) => (
                <button
                  key={p.key}
                  onClick={() =>
                    setPlatforms((prev) => ({
                      ...prev,
                      [p.key as keyof typeof platforms]:
                        !prev[p.key as keyof typeof platforms],
                    }))
                  }
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-bold transition-all ${
                    platforms[p.key as keyof typeof platforms]
                      ? "border-[#FF003C] bg-[#FF003C]/10 text-white"
                      : "border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-white"
                  }`}
                >
                  <span>{p.icon}</span>
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-xl border border-[#FF003C]/30 bg-[#FF003C]/10 p-3">
              <p className="text-sm text-[#FF003C] font-mono">{error}</p>
            </div>
          )}

          {/* Results */}
          {results && (
            <div className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-black p-4">
              <h3 className="text-sm font-bold mb-3">
                {allSuccess ? "✅ Published!" : "⚠️ Results"}
              </h3>
              <div className="space-y-2">
                {results.map((r) => (
                  <div
                    key={r.platform}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="font-medium">
                      {r.platform === "instagram"
                        ? "📸 Instagram"
                        : "▶️ YouTube"}
                    </span>
                    {r.status === "posted" ? (
                      <a
                        href={r.platformUrl || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#00FF66] hover:underline"
                      >
                        ✅ View Post ↗
                      </a>
                    ) : (
                      <span className="text-[#FF003C]">
                        ❌ {r.error || "Failed"}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 text-sm font-bold rounded-xl border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-white transition-colors"
            >
              {results ? "Close" : "Cancel"}
            </button>
            {!results && (
              <button
                onClick={publish}
                disabled={publishing}
                className="flex-1 px-4 py-2.5 text-sm font-bold rounded-xl bg-[#FF003C] text-white hover:shadow-[0_0_15px_rgba(255,0,60,0.2)] transition-all disabled:opacity-50"
              >
                {publishing ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    Publishing...
                  </span>
                ) : (
                  "🚀 Post Now"
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
