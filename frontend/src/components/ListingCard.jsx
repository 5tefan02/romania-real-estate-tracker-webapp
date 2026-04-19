// un card dintr-un grid de anunturi

import { useState } from "react";

// 95000 -> "95.000"
function formatPrice(value) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("ro-RO").format(value);
}

function StatusBadge({ status }) {
  const colors = {
    activ: "bg-green-100 text-green-800",
    inactiv: "bg-gray-200 text-gray-700",
    modificat: "bg-yellow-100 text-yellow-800",
  };
  const className = colors[status] || "bg-gray-100 text-gray-700";
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${className}`}>
      {status || "—"}
    </span>
  );
}

export default function ListingCard({ listing }) {
  const [imageIndex, setImageIndex] = useState(0);

  const images = listing.imagini || [];
  const hasImages = images.length > 0;
  const hasMultiple = images.length > 1;
  const currentImage = hasImages ? images[imageIndex] : null;

  // % ca sa sara din nou la inceput dupa ce ajunge la capat
  function showPrev(event) {
    event.stopPropagation();
    event.preventDefault();
    setImageIndex((i) => (i - 1 + images.length) % images.length);
  }

  function showNext(event) {
    event.stopPropagation();
    event.preventDefault();
    setImageIndex((i) => (i + 1) % images.length);
  }

  const arrowClass =
    "absolute top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center " +
    "rounded-full bg-black/50 text-white text-xl leading-none hover:bg-black/70 " +
    "focus:outline-none";

  return (
    <div className="flex flex-col overflow-hidden rounded-lg bg-white shadow-sm transition hover:shadow-md">
      <div className="relative h-44 w-full bg-gray-200">
        {currentImage ? (
          <img
            // key ca sa se schimbe imaginea, nu sa ramana cea veche afisata
            key={currentImage}
            src={currentImage}
            alt=""
            className="h-full w-full object-cover"
            // daca link-ul e stricat ascund imaginea
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm text-gray-400">
            Fara imagine
          </div>
        )}

        {hasMultiple && (
          <>
            <button
              type="button"
              onClick={showPrev}
              aria-label="Imaginea anterioara"
              className={`${arrowClass} left-2`}
            >
              ‹
            </button>

            <button
              type="button"
              onClick={showNext}
              aria-label="Imaginea urmatoare"
              className={`${arrowClass} right-2`}
            >
              ›
            </button>

            <div className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">
              {imageIndex + 1} / {images.length}
            </div>
          </>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <div className="mb-2 flex items-center justify-between">
          <div className="text-lg font-semibold text-gray-900">
            {formatPrice(listing.pret)} EUR
          </div>
          <StatusBadge status={listing.status} />
        </div>

        <div className="mb-1 text-sm text-gray-700">
          {listing.localitate}
          {listing.judet ? `, ${listing.judet}` : ""}
        </div>

        <div className="mb-2 text-xs text-gray-500">
          {listing.tip_imobiliar || "—"}
          {listing.tip_tranzactie ? ` · ${listing.tip_tranzactie}` : ""}
        </div>

        <div className="mb-3 flex flex-wrap gap-2 text-xs text-gray-600">
          {listing.suprafata != null && (
            <span className="rounded bg-gray-100 px-2 py-0.5">
              {listing.suprafata} mp
            </span>
          )}
          {listing.camere && (
            <span className="rounded bg-gray-100 px-2 py-0.5">
              {listing.camere} camere
            </span>
          )}
          {listing.etaj && (
            <span className="rounded bg-gray-100 px-2 py-0.5">
              etaj {listing.etaj}
            </span>
          )}
          {listing.compartimentare && (
            <span className="rounded bg-gray-100 px-2 py-0.5">
              {listing.compartimentare}
            </span>
          )}
        </div>

        {/* un spacer ca sa impinga footer-ul jos */}
        <div className="flex-1" />

        <div className="flex items-center justify-between border-t pt-2 text-xs text-gray-500">
          <span>
            {listing.platforma || "—"}
            {listing.data_publicare ? ` · ${listing.data_publicare}` : ""}
          </span>
          {listing.url_anunt && (
            <a
              href={listing.url_anunt}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-blue-600 hover:underline"
            >
              Vezi anunt
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
