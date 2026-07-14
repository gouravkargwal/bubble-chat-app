"use client";

export function PaginationBar({
  page,
  totalPages,
  total,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between gap-4 mt-4">
      <span className="text-[10px] font-mono text-[rgba(255,255,255,0.3)]">
        {total} total · Page {page} of {totalPages}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          className="px-2 py-1 text-xs font-mono rounded border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          ««
        </button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="px-3 py-1 text-xs font-mono rounded border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          ‹
        </button>
        <span className="px-3 py-1 text-xs font-mono text-white">{page}</span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="px-3 py-1 text-xs font-mono rounded border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          ›
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          className="px-2 py-1 text-xs font-mono rounded border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.45)] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          »»
        </button>
      </div>
    </div>
  );
}
