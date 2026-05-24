// un card dintr-un grid de anunturi
// pentru admin afisez si butoanele de edit / sterge pe card

import { useState } from "react";
import { useAuth } from "../AuthContext.jsx";
import EditListingModal from "./EditListingModal.jsx";

// 95000 -> "95.000"
function formatPrice(value) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("ro-RO").format(value);
}

export default function ListingCard({ listing, onToggleFavorite, onUpdate, onDelete }) {
  const { user } = useAuth();

  // verific daca utilizatorul curent e admin
  // (folosesc isAdmin in mai multe locuri mai jos pentru afisare conditionata)
  let isAdmin = false;
  if (user && user.role === "admin") {
    isAdmin = true;
  }

  const [imageIndex, setImageIndex] = useState(0);

  // state pentru modalul de edit
  const [showEdit, setShowEdit] = useState(false);

  // state pentru modalul de confirmare la stergere
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const images = listing.imagini || [];
  const hasImages = images.length > 0;
  const hasMultiple = images.length > 1;
  const currentImage = hasImages ? images[imageIndex] : null;

  function handleFavoriteClick(event) {
    event.stopPropagation();
    event.preventDefault();
    if (onToggleFavorite) {
      onToggleFavorite(listing.id, !listing.is_favorite);
    }
  }

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

  // se apeleaza dupa ce admin-ul a salvat modificarile in modal
  // (modalul a facut deja API-call, eu doar propag schimbarile catre pagina parinte)
  function handleSavedFromModal(updates) {
    if (onUpdate) {
      onUpdate(listing.id, updates);
    }
  }

  // se apeleaza cand admin-ul confirma stergerea
  async function handleConfirmDelete() {
    setDeleting(true);
    setDeleteError("");
    try {
      if (onDelete) {
        await onDelete(listing.id);
      }
      // dupa stergere reusita parintele scoate cardul din lista, deci
      // nu mai trebuie sa inchid eu modalul - cardul oricum dispare
    } catch (err) {
      setDeleteError(err.message || "Eroare la stergere");
      setDeleting(false);
    }
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

        {/* butonul de favorite - inima plina daca e la favorite, contur daca nu */}
        <button
          type="button"
          onClick={handleFavoriteClick}
          aria-label={listing.is_favorite ? "Scoate din favorite" : "Adauga la favorite"}
          className="absolute top-2 right-2 flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-xl shadow hover:bg-white"
        >
          <span className={listing.is_favorite ? "text-red-500" : "text-gray-400"}>
            {listing.is_favorite ? "♥" : "♡"}
          </span>
        </button>
      </div>

      <div className="flex flex-1 flex-col p-4">
        <div className="mb-2 text-lg font-semibold text-gray-900">
          {formatPrice(listing.pret)} EUR
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
          {listing.etaj && listing.tip_imobiliar !== "Casa" && (
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

        {/* butoanele de admin - apar doar daca user-ul logat e admin */}
        {isAdmin && (
          <div className="mb-2 flex gap-2">
            <button
              type="button"
              onClick={() => setShowEdit(true)}
              className="rounded bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
            >
              Editeaza
            </button>
            <button
              type="button"
              onClick={() => setShowConfirmDelete(true)}
              className="rounded bg-red-50 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
            >
              Dezactiveaza
            </button>
          </div>
        )}

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

      {/* modalul de editare - apare doar daca admin-ul a apasat "Editeaza" */}
      {showEdit && (
        <EditListingModal
          listing={listing}
          onClose={() => setShowEdit(false)}
          onSave={handleSavedFromModal}
        />
      )}

      {/* modalul de confirmare la stergere */}
      {showConfirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="mb-2 text-lg font-semibold text-gray-800">
              Confirmare dezactivare
            </h3>
            <p className="mb-4 text-sm text-gray-600">
              Sigur dezactivezi anuntul de la {listing.localitate || "?"} -{" "}
              {formatPrice(listing.pret)} EUR? Anuntul va disparea din lista,
              dar ramane in baza de date (istoricul si imaginile se pastreaza).
            </p>

            {deleteError && (
              <div className="mb-3 rounded bg-red-50 p-2 text-xs text-red-700">
                {deleteError}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowConfirmDelete(false)}
                disabled={deleting}
                className="rounded bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
              >
                Anuleaza
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={deleting}
                className="rounded bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:bg-gray-400"
              >
                {deleting ? "Se dezactiveaza..." : "Dezactiveaza"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
