// pagina cu anunturile (filtre + grid + pagini)

// am doua state-uri separate pt filtre: unul pt ce scrie userul si altul
// pt ce a trimis efectiv. Daca ar fi doar unul ar face fetch la fiecare tastare

import { useEffect, useState } from "react";
import * as api from "../api.js";
import { useAuth } from "../AuthContext.jsx";

import FiltersBar from "../components/FiltersBar.jsx";
import ListingCard from "../components/ListingCard.jsx";
import Pagination from "../components/Pagination.jsx";

const EMPTY_FILTERS = {
  judet_id: "",
  localitate_id: "",
  tip_imobiliar_id: "",
  tip_tranzactie_id: "",
  compartimentare_id: "",
  pret_min: "",
  pret_max: "",
  suprafata_min: "",
  suprafata_max: "",
  camere: "",
};

const PAGE_SIZE = 20;

export default function Listings() {
  const { user } = useAuth();

  // verific daca user-ul curent e admin (foloseste asta ca sa afisez butonul de ETL)
  let isAdmin = false;
  if (user && user.role === "admin") {
    isAdmin = true;
  }

  const [options, setOptions] = useState(null);

  const [filters, setFilters] = useState(EMPTY_FILTERS);

  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);

  const [page, setPage] = useState(1);

  const [data, setData] = useState({ total: 0, items: [], page: 1, page_size: PAGE_SIZE });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // state pt butonul de ETL: cat timp se face request-ul, butonul e dezactivat
  // dupa raspuns afisez un mesaj scurt langa buton (succes sau eroare)
  const [etlStarting, setEtlStarting] = useState(false);
  const [etlMessage, setEtlMessage] = useState("");

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

  // dau add/remove la backend si actualizez doar item-ul respectiv local
  // ca sa nu refac fetch la toata pagina
  async function handleToggleFavorite(idAnunt, makeFavorite) {
    try {
      if (makeFavorite) {
        await api.addFavorite(idAnunt);
      } else {
        await api.removeFavorite(idAnunt);
      }
      setData((prev) => ({
        ...prev,
        items: prev.items.map((item) =>
          item.id === idAnunt ? { ...item, is_favorite: makeFavorite } : item,
        ),
      }));
    } catch (err) {
      setError(err.message || "Nu am putut salva favoritul");
    }
  }

  // chemat de ListingCard dupa ce admin-ul a salvat modificarile in modal
  // updates contine campurile noi (pret, suprafata, etaj, camere, id_compartimentare)
  // updatez si campurile derivate (compartimentare) ca sa se vada pe card fara refetch
  function handleUpdateListing(idAnunt, updates) {
    setData((prev) => ({
      ...prev,
      items: prev.items.map((item) => {
        if (item.id !== idAnunt) {
          return item;
        }
        // pentru compartimentare caut numele in optiuni dupa id, ca sa-l afisez pe card
        let numeCompartimentare = item.compartimentare;
        if (updates.id_compartimentare == null) {
          numeCompartimentare = null;
        } else if (options && options.compartimentari) {
          const found = options.compartimentari.find(
            (c) => c.id === updates.id_compartimentare,
          );
          if (found) {
            numeCompartimentare = found.nume;
          }
        }
        return {
          ...item,
          pret: updates.pret,
          suprafata: updates.suprafata,
          etaj: updates.etaj,
          camere: updates.camere,
          id_compartimentare: updates.id_compartimentare,
          compartimentare: numeCompartimentare,
        };
      }),
    }));
  }

  // chemat de ListingCard cand admin-ul confirma stergerea
  // intoarce o promise ca sa stie cardul daca a reusit sau a picat
  async function handleDeleteListing(idAnunt) {
    await api.deleteAdminListing(idAnunt);
    setData((prev) => ({
      ...prev,
      total: Math.max(0, prev.total - 1),
      items: prev.items.filter((item) => item.id !== idAnunt),
    }));
  }

  // butonul de ETL - doar pentru admin
  // fire-and-forget: trimite request si afiseaza mesajul. backend-ul ruleaza
  // ETL-ul intr-un thread separat si raspunde imediat ca a pornit.
  // daca backend-ul zice ca ruleaza deja (400) afisez mesajul de eroare.
  async function handleRunEtl() {
    setEtlStarting(true);
    setEtlMessage("");
    try {
      await api.triggerEtl();
      setEtlMessage("ETL pornit. Vezi consola backend-ului pentru progres.");
    } catch (err) {
      setEtlMessage(err.message || "Eroare la pornire ETL");
    } finally {
      setEtlStarting(false);
    }
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

          {/* butonul de ETL - apare doar pentru admin */}
          {isAdmin && (
            <div className="flex items-center gap-3">
              {etlMessage && (
                <span className="text-xs text-gray-500">{etlMessage}</span>
              )}
              <button
                onClick={handleRunEtl}
                disabled={etlStarting}
                className="rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:bg-gray-400"
              >
                {etlStarting ? "Se porneste..." : "Ruleaza ETL"}
              </button>
            </div>
          )}
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
