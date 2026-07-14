"use client";

import type { CandidateFilters } from "./types";
import { HOOK_LABELS, HOOK_STYLES } from "./helpers";

const PRIORITY_OPTIONS = ["", "high", "medium", "low"];

export function CandidateFilterBar({
  filters,
  onChange,
  onApply,
  onReset,
}: {
  filters: CandidateFilters;
  onChange: (f: CandidateFilters) => void;
  onApply: () => void;
  onReset: () => void;
}) {
  const set = (key: keyof CandidateFilters, value: string) =>
    onChange({ ...filters, [key]: value });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") onApply();
  };

  return (
    <div className="rounded-xl border border-[rgba(255,255,255,0.1)] bg-[#0a0a0a] p-4 mb-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
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

        {/* Hook Type */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Hook Type
          </label>
          <select
            value={filters.hookType}
            onChange={(e) => set("hookType", e.target.value)}
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

        {/* Priority */}
        <div>
          <label className="block text-[10px] font-mono text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-1">
            Priority
          </label>
          <select
            value={filters.priority}
            onChange={(e) => set("priority", e.target.value)}
            className="w-full rounded-lg border border-[rgba(255,255,255,0.1)] bg-black px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#FF003C] transition-colors"
          >
            <option value="">All</option>
            {PRIORITY_OPTIONS.filter(Boolean).map((p) => (
              <option key={p} value={p}>
                {p}
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
            max={70}
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
            max={70}
            value={filters.maxScore}
            onChange={(e) => set("maxScore", e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="70"
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
