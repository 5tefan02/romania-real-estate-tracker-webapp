// pagina de predictii

import { useEffect, useState } from "react";

import * as api from "../api.js";
import { useAuth } from "../AuthContext.jsx";

// tipuri pt care avem model (terenul nu are)
const PREDICTABLE_TYPES = ["Apartament", "Casa"];

// form gol la inceput
const EMPTY_FORM = {
  suprafata: "",
  etaj: "",
  county: "",
  locality: "",
  property_type: "Apartament",
  transaction_type: "vanzare",
  camere: "",
  an_constructie: "",
};


export default function Predictions() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  // info despre modele
  const [modelInfo, setModelInfo] = useState(null);
  const [modelInfoError, setModelInfoError] = useState("");

  // retrain (doar admin)
  const [retraining, setRetraining] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);
  const [retrainError, setRetrainError] = useState("");

  // optiuni pt dropdown
  const [options, setOptions] = useState(null);

  // localitati per judet (dupa ce antrenez modelul)
  const [localitiesByCounty, setLocalitiesByCounty] = useState({});

  // formularul
  const [form, setForm] = useState(EMPTY_FORM);

  // predictie
  const [predicting, setPredicting] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [predictError, setPredictError] = useState("");

  // la mount iau toate datele
  useEffect(() => {
    api
      .fetchModelInfo()
      .then(setModelInfo)
      .catch((err) => setModelInfoError(err.message || "Nu am putut lua info despre modele"));

    // folosesc endpoint-ul de la statistici (aceleasi date)
    api
      .fetchStatsFilterOptions()
      .then(setOptions)
      .catch(() => setOptions({ counties: [], property_types: [], transaction_types: [] }));

    // localitatile pe care le stie modelul
    api
      .fetchMlLocalities()
      .then(setLocalitiesByCounty)
      .catch(() => setLocalitiesByCounty({}));
  }, []);

  async function handleRetrain() {
    setRetraining(true);
    setRetrainError("");
    setRetrainResult(null);
    try {
      const res = await api.retrainModels();
      setRetrainResult(res);
      // iau din nou info ca sa apara data noua
      const info = await api.fetchModelInfo();
      setModelInfo(info);
    } catch (err) {
      setRetrainError(err.message || "Nu a mers retrain-ul");
    } finally {
      setRetraining(false);
    }
  }

  function handleFormChange(key, value) {
    setForm((f) => {
      const next = { ...f, [key]: value };
      // daca schimb judetul trebuie sa resetez localitatea
      if (key === "county") next.locality = "";

      // nu am model pt casa + inchiriere, deci le blochez
      if (key === "property_type" && value === "Casa" && next.transaction_type === "inchiriere") {
        next.transaction_type = "vanzare";
      }
      if (key === "transaction_type" && value === "inchiriere" && next.property_type === "Casa") {
        next.property_type = "Apartament";
      }
      return next;
    });
  }

  async function handlePredict(e) {
    e.preventDefault();
    setPredicting(true);
    setPredictError("");
    setPrediction(null);

    // convertesc din string in int (de la input)
    const payload = {
      suprafata: parseInt(form.suprafata, 10) || 0,
      etaj: parseInt(form.etaj, 10) || 0,
      county: form.county,
      // daca nu a ales localitate ii dau "alta"
      locality: form.locality || "alta",
      property_type: form.property_type,
      transaction_type: form.transaction_type,
      camere: parseInt(form.camere, 10) || 0,
      an_constructie: parseInt(form.an_constructie, 10) || 0,
    };

    try {
      const res = await api.predictPrice(payload);
      setPrediction(res);
    } catch (err) {
      setPredictError(err.message || "Nu a mers predictia");
    } finally {
      setPredicting(false);
    }
  }

  const inputClass =
    "w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none";

  // cat timp nu am raspuns
  const modelsLoaded = modelInfo !== null;
  const modelsTrained = modelInfo?.models_trained === true;
  const formDisabled = !modelsTrained;

  // cheia modelului ales
  const selectedModelKey =
    form.property_type && form.transaction_type
      ? `${form.property_type === "Casa" ? "casa" : "apartament"}_${form.transaction_type}`
      : null;

  // metricele pt modelul ales
  const selectedModelMetrics = selectedModelKey ? modelInfo?.[selectedModelKey] : null;

  // ascund inchirierea daca e casa
  const availablePropertyTypes =
    form.transaction_type === "inchiriere" ? ["Apartament"] : PREDICTABLE_TYPES;
  const canRentCurrentType = form.property_type !== "Casa";

  // format pt afisare pret
  const formatEur = (n) =>
    n == null ? "—" : `${Math.round(n).toLocaleString("en-US")} €`;

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-5xl p-6">
        <h1 className="mb-4 text-2xl font-semibold text-gray-800">Estimare pret</h1>

        {/* bara cu starea modelelor */}
        <div className="rounded-lg bg-white p-4 shadow-sm">
          {modelInfoError && (
            <div className="mb-2 rounded bg-red-50 p-2 text-sm text-red-700">
              {modelInfoError}
            </div>
          )}

          {!modelsLoaded && !modelInfoError && (
            <div className="text-sm text-gray-500">Se incarca...</div>
          )}

          {modelsLoaded && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm">
                <span
                  className={`inline-block h-3 w-3 rounded-full ${
                    modelsTrained ? "bg-green-500" : "bg-red-500"
                  }`}
                ></span>
                {modelsTrained ? (
                  <span className="text-gray-800">
                    Modelele sunt antrenate. Ultima data: {modelInfo.last_trained}
                  </span>
                ) : (
                  <span className="text-gray-800">
                    Modelele nu sunt antrenate
                  </span>
                )}
              </div>

              {isAdmin && (
                <button
                  onClick={handleRetrain}
                  disabled={retraining}
                  className="flex items-center gap-2 rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-blue-400"
                >
                  {retraining && (
                    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
                  )}
                  {retraining ? "Se antreneaza..." : "Antreneaza din nou"}
                </button>
              )}
            </div>
          )}

          {retrainError && (
            <div className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">
              {retrainError}
            </div>
          )}

          {/* tabelul cu rezultatele dupa antrenare */}
          {retrainResult && (
            <div className="mt-4">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-2">Model</th>
                    <th className="px-3 py-2">Anunturi</th>
                    <th className="px-3 py-2">MAE</th>
                    <th className="px-3 py-2">R² Score</th>
                  </tr>
                </thead>
                <tbody className="text-gray-800">
                  <tr className="border-t">
                    <td className="px-3 py-2">Random Forest (Apartament — Vanzare)</td>
                    <td className="px-3 py-2">{retrainResult.apartament_vanzare.training_rows}</td>
                    <td className="px-3 py-2">{formatEur(retrainResult.apartament_vanzare.mae)}</td>
                    <td className="px-3 py-2">{retrainResult.apartament_vanzare.r2}</td>
                  </tr>
                  <tr className="border-t">
                    <td className="px-3 py-2">Random Forest (Casa — Vanzare)</td>
                    <td className="px-3 py-2">{retrainResult.casa_vanzare.training_rows}</td>
                    <td className="px-3 py-2">{formatEur(retrainResult.casa_vanzare.mae)}</td>
                    <td className="px-3 py-2">{retrainResult.casa_vanzare.r2}</td>
                  </tr>
                  <tr className="border-t">
                    <td className="px-3 py-2">Random Forest (Apartament — Inchiriere)</td>
                    <td className="px-3 py-2">{retrainResult.apartament_inchiriere.training_rows}</td>
                    <td className="px-3 py-2">{formatEur(retrainResult.apartament_inchiriere.mae)}</td>
                    <td className="px-3 py-2">{retrainResult.apartament_inchiriere.r2}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6 rounded-lg bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-800">
            Afla cat poate sa coste un imobil
          </h2>
          <form onSubmit={handlePredict}>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Suprafata (m²)
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  disabled={formDisabled}
                  className={inputClass}
                  value={form.suprafata}
                  onChange={(e) => handleFormChange("suprafata", e.target.value)}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Etaj</label>
                <input
                  type="number"
                  min="0"
                  disabled={formDisabled}
                  className={inputClass}
                  value={form.etaj}
                  onChange={(e) => handleFormChange("etaj", e.target.value)}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Judet</label>
                <select
                  required
                  disabled={formDisabled || !options}
                  className={inputClass}
                  value={form.county}
                  onChange={(e) => handleFormChange("county", e.target.value)}
                >
                  <option value="">-- alege --</option>
                  {options?.counties.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Localitate
                </label>
                <select
                  disabled={formDisabled || !form.county}
                  className={inputClass}
                  value={form.locality}
                  onChange={(e) => handleFormChange("locality", e.target.value)}
                >
                  <option value="">
                    {form.county ? "-- alege (daca vrei) --" : "alege judetul mai intai"}
                  </option>
                  {(localitiesByCounty[form.county] || []).map((loc) => (
                    <option key={loc} value={loc}>
                      {loc === "alta" ? "Alta" : loc}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Tip imobil
                </label>
                <select
                  required
                  disabled={formDisabled}
                  className={inputClass}
                  value={form.property_type}
                  onChange={(e) => handleFormChange("property_type", e.target.value)}
                >
                  {availablePropertyTypes.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Tranzactie
                </label>
                <select
                  disabled={formDisabled}
                  className={inputClass}
                  value={form.transaction_type}
                  onChange={(e) => handleFormChange("transaction_type", e.target.value)}
                >
                  <option value="vanzare">Vanzare</option>
                  {canRentCurrentType && <option value="inchiriere">Inchiriere</option>}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Numar camere
                </label>
                <input
                  type="number"
                  min="0"
                  disabled={formDisabled}
                  className={inputClass}
                  value={form.camere}
                  onChange={(e) => handleFormChange("camere", e.target.value)}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  An constructie
                </label>
                <input
                  type="number"
                  min="1900"
                  max="2100"
                  disabled={formDisabled}
                  className={inputClass}
                  value={form.an_constructie}
                  onChange={(e) => handleFormChange("an_constructie", e.target.value)}
                />
              </div>
            </div>

            <div className="mt-4">
              <button
                type="submit"
                disabled={formDisabled || predicting}
                className="flex items-center gap-2 rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-blue-400"
              >
                {predicting && (
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
                )}
                {predicting ? "Se calculeaza..." : "Arata-mi pretul"}
              </button>
            </div>
          </form>

          {predictError && (
            <div className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">
              {predictError}
            </div>
          )}

          {/* card cu rezultatul */}
          {prediction && (
            <>
              <div className="mt-5 grid grid-cols-1 gap-3">
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
                  <div className="text-xs font-medium uppercase text-gray-500">
                    Random Forest — {prediction.model_type}
                    {" ("}
                    {prediction.transaction_type === "inchiriere" ? "Inchiriere" : "Vanzare"}
                    {")"}
                  </div>
                  <div className="mt-2 text-2xl font-semibold text-gray-800">
                    {formatEur(prediction.price)}
                    {prediction.transaction_type === "inchiriere" && (
                      <span className="text-base font-normal text-gray-500"> / luna</span>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
