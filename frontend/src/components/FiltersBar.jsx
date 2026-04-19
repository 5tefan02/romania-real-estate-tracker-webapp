// bara cu filtre (o folosesc la Listings)
// primeste totul din parinte si doar afiseaza + trimite evenimente

export default function FiltersBar({ options, filters, onChange, onApply, onReset }) {
  if (!options) {
    return <div className="p-4 text-sm text-gray-500">Se incarca filtrele...</div>;
  }

  // daca are ales judet, arat doar localitatile din judetul ala
  const localitatiForJudet = filters.judet_id
    ? options.localitati.filter(
        (l) => String(l.id_judet) === String(filters.judet_id),
      )
    : options.localitati;

  const inputClass =
    "w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none";

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Judet</label>
          <select
            className={inputClass}
            value={filters.judet_id}
            onChange={(e) => {
              onChange("judet_id", e.target.value);
              // daca schimba judetul, resetez localitatea
              onChange("localitate_id", "");
            }}
          >
            <option value="">Toate</option>
            {options.judete.map((j) => (
              <option key={j.id} value={j.id}>
                {j.nume}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Localitate</label>
          <select
            className={inputClass}
            value={filters.localitate_id}
            onChange={(e) => onChange("localitate_id", e.target.value)}
          >
            <option value="">Toate</option>
            {localitatiForJudet.map((l) => (
              <option key={l.id} value={l.id}>
                {l.nume}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Tip imobil</label>
          <select
            className={inputClass}
            value={filters.tip_imobiliar_id}
            onChange={(e) => onChange("tip_imobiliar_id", e.target.value)}
          >
            <option value="">Toate</option>
            {options.tipuri_imobil.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nume}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Tranzactie</label>
          <select
            className={inputClass}
            value={filters.tip_tranzactie_id}
            onChange={(e) => onChange("tip_tranzactie_id", e.target.value)}
          >
            <option value="">Toate</option>
            {options.tipuri_tranzactie.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nume}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Compartimentare</label>
          <select
            className={inputClass}
            value={filters.compartimentare_id}
            onChange={(e) => onChange("compartimentare_id", e.target.value)}
          >
            <option value="">Toate</option>
            {options.compartimentari.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nume}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Status</label>
          <select
            className={inputClass}
            value={filters.status_anunt}
            onChange={(e) => onChange("status_anunt", e.target.value)}
          >
            <option value="">Toate</option>
            <option value="activ">Activ</option>
            <option value="inactiv">Inactiv</option>
            <option value="modificat">Modificat</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Pret (EUR)</label>
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              placeholder="min"
              className={inputClass}
              value={filters.pret_min}
              onChange={(e) => onChange("pret_min", e.target.value)}
            />
            <input
              type="number"
              min="0"
              placeholder="max"
              className={inputClass}
              value={filters.pret_max}
              onChange={(e) => onChange("pret_max", e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Suprafata (mp)</label>
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              placeholder="min"
              className={inputClass}
              value={filters.suprafata_min}
              onChange={(e) => onChange("suprafata_min", e.target.value)}
            />
            <input
              type="number"
              min="0"
              placeholder="max"
              className={inputClass}
              value={filters.suprafata_max}
              onChange={(e) => onChange("suprafata_max", e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={onApply}
          className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Aplica
        </button>
        <button
          onClick={onReset}
          className="rounded bg-gray-200 px-4 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-300"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
