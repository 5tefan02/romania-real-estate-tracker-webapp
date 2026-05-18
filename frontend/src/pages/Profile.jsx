// pagina de profil - afiseaza datele contului si formularul pentru
// filtrele de notificari pe mail

import { useEffect, useState } from "react";
import * as api from "../api.js";
import { useAuth } from "../AuthContext.jsx";

// in state se foloseste "" in loc de null, pentru ca <select>-urile din React
// se plang daca primesc value=null (le considera uncontrolled)
const EMPTY_CRITERII = {
  id_judet: "",
  id_localitate: "",
  id_tip_imobiliar: "",
  id_tip_tranzactie: "",
  id_compartimentare: "",
  pret_min: "",
  pret_max: "",
  suprafata_min: "",
  suprafata_max: "",
  camere: "",
  activ: true,
};

// backend-ul trimite null pe campurile pe care userul nu le-a setat
// dar formularul are nevoie de "" (vezi mai sus), deci se converteste null -> ""
function critFromApi(crit) {
  return {
    id_judet: crit.id_judet ?? "",
    id_localitate: crit.id_localitate ?? "",
    id_tip_imobiliar: crit.id_tip_imobiliar ?? "",
    id_tip_tranzactie: crit.id_tip_tranzactie ?? "",
    id_compartimentare: crit.id_compartimentare ?? "",
    pret_min: crit.pret_min ?? "",
    pret_max: crit.pret_max ?? "",
    suprafata_min: crit.suprafata_min ?? "",
    suprafata_max: crit.suprafata_max ?? "",
    camere: crit.camere ?? "",
    activ: crit.activ,
  };
}

export default function Profile() {
  const { user } = useAuth();
  const [options, setOptions] = useState(null);
  const [criterii, setCriterii] = useState(EMPTY_CRITERII);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // la incarcarea paginii se aduc 2 lucruri in paralel cu Promise.all:
  // - lista cu judete/localitati/tipuri (pentru dropdown-uri)
  // - criteriile salvate inainte de user (daca exista)
  useEffect(() => {
    Promise.all([api.fetchFilters(), api.fetchCriterii()])
      .then(([opts, crit]) => {
        setOptions(opts);
        if (crit) {
          setCriterii(critFromApi(crit));
        }
      })
      .catch((err) => setError(err.message || "Eroare la incarcare"))
      .finally(() => setLoading(false));
  }, []);

  function handleChange(key, value) {
    setCriterii((c) => ({ ...c, [key]: value }));
    // dupa o salvare reusita ramane mesajul verde "Salvat"
    // la urmatoarea modificare se sterge, ca sa nu para ca e tot salvat
    setSuccess("");
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      // backend-ul asteapta int sau null pe fiecare camp,
      // dar in formular sunt string-uri ("" cand e gol, "12" cand e ales ceva)
      // deci se converteste: "" -> null, "12" -> 12
      // (campul "activ" e boolean, ramane cum e)
      const toSend = {};
      for (const [key, value] of Object.entries(criterii)) {
        if (key === "activ") {
          toSend[key] = value;
        } else if (value === "" || value === null) {
          toSend[key] = null;
        } else {
          toSend[key] = Number(value);
        }
      }
      const saved = await api.saveCriterii(toSend);
      setSuccess("Profilul a fost salvat.");
      setCriterii(critFromApi(saved));
    } catch (err) {
      setError(err.message || "Eroare la salvare");
    } finally {
      setSaving(false);
    }
  }

  // daca userul a ales un judet, in dropdown apar doar localitatile din acel judet
  // (altfel ar fi toate localitatile din tara, ar fi prea multe)
  // String(...) ca sa nu se incurce comparatia dintre numar si string
  const localitatiForJudet =
    options && criterii.id_judet
      ? options.localitati.filter(
          (l) => String(l.id_judet) === String(criterii.id_judet),
        )
      : options?.localitati ?? [];

  const inputClass =
    "w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none";

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-3xl space-y-6 p-6">
        <h1 className="text-2xl font-semibold text-gray-800">Profilul meu</h1>

        {/* sus apar datele contului (read-only, doar info) */}
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-800">Contul meu</h2>
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-gray-500">Username</dt>
              <dd className="text-gray-800">{user?.username}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Email</dt>
              <dd className="text-gray-800">{user?.email}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Rol</dt>
              <dd className="text-gray-800">{user?.role}</dd>
            </div>
          </dl>
        </section>

        {/* mai jos e formularul cu filtrele pentru notificari */}
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="mb-2 text-lg font-medium text-gray-800">
            Notificari pe email
          </h2>
          <p className="mb-4 text-sm text-gray-600">
            Configureaza ce anunturi te intereseaza. Cand apar anunturi noi
            care se potrivesc, primesti un email.
          </p>

          {loading && (
            <div className="text-sm text-gray-500">Se incarca...</div>
          )}

          {!loading && options && (
            <>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Judet
                  </label>
                  <select
                    className={inputClass}
                    value={criterii.id_judet}
                    onChange={(e) => {
                      handleChange("id_judet", e.target.value);
                      // la schimbarea judetului, vechea localitate
                      // probabil nu mai apartine de el -> se reseteaza
                      handleChange("id_localitate", "");
                    }}
                  >
                    <option value="">Orice</option>
                    {options.judete.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.nume}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Localitate
                  </label>
                  <select
                    className={inputClass}
                    value={criterii.id_localitate}
                    onChange={(e) =>
                      handleChange("id_localitate", e.target.value)
                    }
                  >
                    <option value="">Orice</option>
                    {localitatiForJudet.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.nume}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Tip imobil
                  </label>
                  <select
                    className={inputClass}
                    value={criterii.id_tip_imobiliar}
                    onChange={(e) =>
                      handleChange("id_tip_imobiliar", e.target.value)
                    }
                  >
                    <option value="">Orice</option>
                    {options.tipuri_imobil.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.nume}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Tranzactie
                  </label>
                  <select
                    className={inputClass}
                    value={criterii.id_tip_tranzactie}
                    onChange={(e) =>
                      handleChange("id_tip_tranzactie", e.target.value)
                    }
                  >
                    <option value="">Orice</option>
                    {options.tipuri_tranzactie.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.nume}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Compartimentare
                  </label>
                  <select
                    className={inputClass}
                    value={criterii.id_compartimentare}
                    onChange={(e) =>
                      handleChange("id_compartimentare", e.target.value)
                    }
                  >
                    <option value="">Orice</option>
                    {options.compartimentari.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nume}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Pret (EUR)
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min="0"
                      placeholder="min"
                      className={inputClass}
                      value={criterii.pret_min}
                      onChange={(e) => handleChange("pret_min", e.target.value)}
                    />
                    <input
                      type="number"
                      min="0"
                      placeholder="max"
                      className={inputClass}
                      value={criterii.pret_max}
                      onChange={(e) => handleChange("pret_max", e.target.value)}
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Suprafata (mp)
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min="0"
                      placeholder="min"
                      className={inputClass}
                      value={criterii.suprafata_min}
                      onChange={(e) =>
                        handleChange("suprafata_min", e.target.value)
                      }
                    />
                    <input
                      type="number"
                      min="0"
                      placeholder="max"
                      className={inputClass}
                      value={criterii.suprafata_max}
                      onChange={(e) =>
                        handleChange("suprafata_max", e.target.value)
                      }
                    />
                  </div>
                </div>

                {/* numarul de camere - match exact. daca e gol = "orice numar" */}
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    Numar camere
                  </label>
                  <input
                    type="number"
                    min="1"
                    placeholder="orice"
                    className={inputClass}
                    value={criterii.camere}
                    onChange={(e) => handleChange("camere", e.target.value)}
                  />
                </div>
              </div>

              {/* bifa pentru pornit/oprit notificarile - daca e debifata
                  userul nu mai primeste mailuri pana o bifeaza din nou */}
              <label className="mt-4 flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-gray-300"
                  checked={criterii.activ}
                  onChange={(e) => handleChange("activ", e.target.checked)}
                />
                Trimite-mi emailuri cu anunturile noi care corespund
              </label>

              {error && (
                <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </div>
              )}
              {success && (
                <div className="mt-4 rounded bg-green-50 p-3 text-sm text-green-700">
                  {success}
                </div>
              )}

              <div className="mt-4">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {saving ? "Se salveaza..." : "Salveaza"}
                </button>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
