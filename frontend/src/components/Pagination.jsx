// butoanele de pagini (prev / next)

export default function Pagination({ page, totalPages, onChange }) {
  const canPrev = page > 1;
  const canNext = page < totalPages;

  const buttonClass =
    "rounded bg-white px-3 py-1 text-sm shadow-sm ring-1 ring-gray-200 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <div className="flex items-center justify-center gap-3 py-6">
      <button
        className={buttonClass}
        disabled={!canPrev}
        onClick={() => onChange(page - 1)}
      >
        ← Inapoi
      </button>
      <span className="text-sm text-gray-600">
        Pagina {page} din {totalPages}
      </span>
      <button
        className={buttonClass}
        disabled={!canNext}
        onClick={() => onChange(page + 1)}
      >
        Inainte →
      </button>
    </div>
  );
}
