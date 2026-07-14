"use client";

import type { RenderedFilters } from "./types";
import { HOOK_LABELS, HOOK_STYLES, STATUS_OPTIONS } from "./helpers";

export function FilterBar({
  filters,
  onChange,
  onApply,
  onReset,
}: {
  filters: RenderedFilters;
  onChange: (f: RenderedFilters) => void;
  onApply: () => void;
  onReset: () => void;
}) {
  const set = (key: keyof RenderedFilters, value: string) =>
    onChange({ ...filters, [key]: value });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") onApply();
  };

  return (
    <div className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a] p-4 mb-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Search */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Search
          </label>
          <input
            type="text"
            value={filters.search}
            onChange={(e) => set("search", e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Name..."
            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-black px-3 py-2 text-xs font-mono text-white placeholder-[rgba(255,255,255,0.25)] focus:outline-none focus:border-[#FF003C] transition-colors"
          />
        </div>

        {/* Status */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Status
          </label>
          <select
            value={filters.status}
            onChange={(e) => set("status", e.target.value)}
            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-black px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#FF003C] transition-colors"
          >
            <option value="">All</option>
            {STATUS_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Hook Style */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Hook Style
          </label>
          <select
            value={filters.hookStyle}
            onChange={(e) => set("hookStyle", e.target.value)}
            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-black px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#FF003C] transition-colors"
          >
            <option value="">All</option>
            {HOOK_STYLES.map((s) => (
              <option key={s} value={s}>
                {HOOK_LABELS[s]}
              </option>
            ))}
          </select>
        </div>

        {/* Min Score */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Min Score
          </label>
          <input
            type="number"
            min={0}
            max={100}
            value={filters.minScore}
            onChange={(e) => set("minScore", e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="0"
            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-black px-3 py-2 text-xs font-mono text-white placeholder-[rgba(255,255,255,0.25)] focus:outline-none focus:border-[#FF003C] transition-colors"
          />
        </div>

        {/* Max Score */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Max Score
          </label>
          <input
            type="number"
            min={0}
            max={100}
            value={filters.maxScore}
            onChange={(e) => set("maxScore", e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="100"
            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-black px-3 py-2 text-xs font-mono text-white placeholder-[rgba(255,255,255,0.25)] focus:outline-none focus:border-[#FF003C] transition-colors"
          />
        </div>

        {/* Strategy Label */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Strategy
          </label>
          <input
            type="text"
            value={filters.strategyLabel}
            onChange={(e) => set("strategyLabel", e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. COOKD_AI"
            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-black px-3 py-2 text-xs font-mono text-white placeholder-[rgba(255,255,255,0.25)] focus:outline-none focus:border-[#FF003C] transition-colors"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={onApply}
          className="px-4 py-1.5 text-xs font-bold rounded-full bg-[#FF003C] text-white hover:shadow-[0_0_15px_rgba(255,0,60,0.2)] transition-all"
        >
          Apply Filters
        </button>
        <button
          onClick={onReset}
          className="px-4 py-1.5 text-xs font-bold rounded-full border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-white transition-all"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
