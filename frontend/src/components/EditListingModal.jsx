// modal pentru editat un anunt (doar admin)
// se afiseaza peste pagina, are formular cu campurile editabile si butoane
// foloseste acelasi pattern cu inputClass ca restul formularelor din proiect

import { useEffect, useState } from "react";
import * as api from "../api.js";

export default function EditListingModal({ listing, onClose, onSave }) {
  // state-ul formularului - tin string in input-uri (asa cere React la <input>)
  // chiar si la numere; la salvare convertesc inapoi la int sau null
  const [pret, setPret] = useState("");
  const [suprafata, setSuprafata] = useState("");
  const [etaj, setEtaj] = useState("");
  const [camere, setCamere] = useState("");
  const [idCompartimentare, setIdCompartimentare] = useState("");

  // lista de compartimentari pentru dropdown - se ia o data la deschidere
  const [compartimentari, setCompartimentari] = useState([]);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // la deschidere prefilesc formularul cu valorile actuale ale anuntului
  // si iau lista de compartimentari de la backend
  useEffect(() => {
    // ?? "" ca sa transform null/undefined in string gol pentru input-uri
    setPret(listing.pret == null ? "" : String(listing.pret));
    setSuprafata(listing.suprafata == null ? "" : String(listing.suprafata));
    setEtaj(listing.etaj == null ? "" : String(listing.etaj));
    setCamere(listing.camere == null ? "" : String(listing.camere));
    setIdCompartimentare(
      listing.id_compartimentare == null ? "" : String(listing.id_compartimentare),
    );

    // iau optiunile - acelasi endpoint ca pe pagina de listings
    api
      .fetchFilters()
      .then((opts) => {
        setCompartimentari(opts.compartimentari || []);
      })
      .catch(() => {
        // daca pica fetch-ul las dropdown-ul gol, nu blochez restul formularului
        setCompartimentari([]);
      });
  }, [listing]);

  // converteste un string din input intr-un numar sau null
  // ("" sau valoare invalida -> null, altfel intoarce intregul)
  function toIntOrNull(value) {
    if (value === "" || value === null) {
      return null;
    }
    const n = Number(value);
    if (Number.isNaN(n)) {
      return null;
    }
    return n;
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      // construiesc payload-ul - convertesc fiecare camp inainte sa-l trimit
      const payload = {
        pret: toIntOrNull(pret),
        suprafata: toIntOrNull(suprafata),
        etaj: etaj === "" ? null : etaj,
        camere: toIntOrNull(camere),
        id_compartimentare: toIntOrNull(idCompartimentare),
      };

      await api.updateAdminListing(listing.id, payload);

      // anunt parintele de noile valori ca sa actualizeze cardul fara refetch
      if (onSave) {
        onSave(payload);
      }
      onClose();
    } catch (err) {
      setError(err.message || "Eroare la salvare");
    } finally {
      setSaving(false);
    }
  }

  const inputClass =
    "w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="mb-4 text-lg font-semibold text-gray-800">
          Editeaza anuntul
        </h3>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Pret (EUR)
            </label>
            <input
              type="number"
              min="0"
              className={inputClass}
              value={pret}
              onChange={(e) => setPret(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Suprafata (mp)
            </label>
            <input
              type="number"
              min="0"
              className={inputClass}
              value={suprafata}
              onChange={(e) => setSuprafata(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Etaj
            </label>
            <input
              type="text"
              className={inputClass}
              value={etaj}
              onChange={(e) => setEtaj(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Camere
            </label>
            <input
              type="number"
              min="0"
              className={inputClass}
              value={camere}
              onChange={(e) => setCamere(e.target.value)}
            />
          </div>

          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Compartimentare
            </label>
            <select
              className={inputClass}
              value={idCompartimentare}
              onChange={(e) => setIdCompartimentare(e.target.value)}
            >
              <option value="">-</option>
              {compartimentari.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nume}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={saving}
            className="rounded bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
          >
            Anuleaza
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-400"
          >
            {saving ? "Se salveaza..." : "Salveaza"}
          </button>
        </div>
      </div>
    </div>
  );
}
