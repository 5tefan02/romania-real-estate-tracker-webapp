// pagina cu anunturile (filtre + grid + pagini)

// am doua state-uri separate pt filtre: unul pt ce scrie userul si altul
// pt ce a trimis efectiv. Daca ar fi doar unul ar face fetch la fiecare tastare

import { useEffect, useState } from "react";
import * as api from "../api.js";

import FiltersBar from "../components/FiltersBar.jsx";
import ListingCard from "../components/ListingCard.jsx";
import Pagination from "../components/Pagination.jsx";

const EMPTY_FILTERS = {
  judet_id: "",
  localitate_id: "",
  tip_imobiliar_id: "",
  tip_tranzactie_id: "",
  compartimentare_id: "",
  status_anunt: "",
  pret_min: "",
  pret_max: "",
  suprafata_min: "",
  suprafata_max: "",
};

const PAGE_SIZE = 20;

export default function Listings() {
  const [options, setOptions] = useState(null);

  const [filters, setFilters] = useState(EMPTY_FILTERS);

  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);

  const [page, setPage] = useState(1);

  const [data, setData] = useState({ total: 0, items: [], page: 1, page_size: PAGE_SIZE });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // iau optiunile la mount
  useEffect(() => {
    api
      .fetchFilters()
      .then(setOptions)
      .catch((err) => setError(err.message || "Nu am putut lua filtrele"));
  }, []);

  // dau fetch cand se schimba filtrele sau pagina
  useEffect(() => {
    setLoading(true);
    setError("");
    api
      .fetchListings({ ...appliedFilters, page, page_size: PAGE_SIZE })
      .then(setData)
      .catch((err) => setError(err.message || "Nu am putut lua anunturile"))
      .finally(() => setLoading(false));
  }, [appliedFilters, page]);

  function handleFilterChange(key, value) {
    // forma cu functie ca sa nu pierd update-uri cand vin mai multe deodata
    setFilters((f) => ({ ...f, [key]: value }));
  }

  function handleApply() {
    setAppliedFilters(filters);
    setPage(1);
  }

  function handleReset() {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
  }

  // macar 1 pagina ca sa nu apara 0
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-7xl p-6">
        <FiltersBar
          options={options}
          filters={filters}
          onChange={handleFilterChange}
          onApply={handleApply}
          onReset={handleReset}
        />

        <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
          <div>
            {loading ? "Se incarca..." : `${data.total} rezultate`}
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && data.items.length === 0 && !error && (
          <div className="mt-6 rounded-lg bg-white p-8 text-center text-gray-500 shadow-sm">
            Nu am gasit niciun anunt.
          </div>
        )}

        {data.items.length > 0 && (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.items.map((listing) => (
              <ListingCard key={listing.id} listing={listing} />
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
