// pagina cu anunturile favorite ale user-ului
// foloseste aceleasi carduri ca Listings, doar fetch-ul e diferit

import { useEffect, useState } from "react";
import * as api from "../api.js";

import ListingCard from "../components/ListingCard.jsx";
import Pagination from "../components/Pagination.jsx";

const PAGE_SIZE = 20;

export default function Favorites() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ total: 0, items: [], page: 1, page_size: PAGE_SIZE });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // fetch la mount si la schimbare de pagina
  useEffect(() => {
    setLoading(true);
    setError("");
    api
      .fetchFavorites({ page, page_size: PAGE_SIZE })
      .then(setData)
      .catch((err) => setError(err.message || "Nu am putut lua favoritele"))
      .finally(() => setLoading(false));
  }, [page]);

  // cand userul scoate ceva din favorite pe pagina asta il scot direct din lista
  // (altfel ar ramane afisat dar cu inima goala)
  async function handleToggleFavorite(idAnunt, makeFavorite) {
    try {
      if (makeFavorite) {
        await api.addFavorite(idAnunt);
        setData((prev) => ({
          ...prev,
          items: prev.items.map((item) =>
            item.id === idAnunt ? { ...item, is_favorite: true } : item,
          ),
        }));
      } else {
        await api.removeFavorite(idAnunt);
        setData((prev) => ({
          ...prev,
          total: Math.max(0, prev.total - 1),
          items: prev.items.filter((item) => item.id !== idAnunt),
        }));
      }
    } catch (err) {
      setError(err.message || "Nu am putut salva favoritul");
    }
  }

  // chemat de ListingCard dupa ce admin-ul a salvat modificarile in modal
  // aici nu am lista de compartimentari la indemana (nu fac fetchFilters pe pagina
  // asta), deci pentru compartimentare las valoarea veche pana la urmatorul refresh
  function handleUpdateListing(idAnunt, updates) {
    setData((prev) => ({
      ...prev,
      items: prev.items.map((item) => {
        if (item.id !== idAnunt) {
          return item;
        }
        return {
          ...item,
          pret: updates.pret,
          suprafata: updates.suprafata,
          etaj: updates.etaj,
          camere: updates.camere,
          id_compartimentare: updates.id_compartimentare,
        };
      }),
    }));
  }

  // chemat de ListingCard cand admin-ul confirma stergerea anuntului
  async function handleDeleteListing(idAnunt) {
    await api.deleteAdminListing(idAnunt);
    setData((prev) => ({
      ...prev,
      total: Math.max(0, prev.total - 1),
      items: prev.items.filter((item) => item.id !== idAnunt),
    }));
  }

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-7xl p-6">
        <h1 className="mb-4 text-xl font-semibold text-gray-800">Favoritele mele</h1>

        <div className="text-sm text-gray-600">
          {loading ? "Se incarca..." : `${data.total} anunturi salvate`}
        </div>

        {error && (
          <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && data.items.length === 0 && !error && (
          <div className="mt-6 rounded-lg bg-white p-8 text-center text-gray-500 shadow-sm">
            Nu ai niciun anunt salvat la favorite.
          </div>
        )}

        {data.items.length > 0 && (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.items.map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                onToggleFavorite={handleToggleFavorite}
                onUpdate={handleUpdateListing}
                onDelete={handleDeleteListing}
              />
            ))}
          </div>
        )}

        {data.total > 0 && (
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        )}
      </main>
    </div>
  );
}
