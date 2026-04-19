// pagina de statistici cu grafice

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import * as api from "../api.js";

// filtre goale
const EMPTY_FILTERS = {
  county: "",
  transaction_type: "",
  property_type: "",
};

// culori pt pie si bare
const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

// un card pt fiecare grafic (titlu + loading + error + continut)
function ChartCard({ title, loading, error, isEmpty, children }) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-gray-800">{title}</h2>

      {loading && (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-500"></div>
        </div>
      )}

      {!loading && error && (
        <div className="flex h-64 items-center justify-center rounded bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && isEmpty && (
        <div className="flex h-64 items-center justify-center text-sm text-gray-500">
          Nu sunt date pt filtrele alese.
        </div>
      )}

      {!loading && !error && !isEmpty && children}
    </div>
  );
}

export default function Statistics() {
  // optiuni pt dropdown-uri (le iau o data)
  const [options, setOptions] = useState(null);
  const [optionsError, setOptionsError] = useState("");

  // ce tasteaza userul
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  // ce s a aplicat efectiv (cand apasa Apply)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);

  // cate un state pt fiecare grafic
  const [trend, setTrend] = useState({ data: [], loading: true, error: "" });
  const [distribution, setDistribution] = useState({ data: [], loading: true, error: "" });
  const [platforms, setPlatforms] = useState({ data: [], loading: true, error: "" });
  const [pps, setPps] = useState({ data: [], loading: true, error: "" });

  // la mount iau optiunile
  useEffect(() => {
    api
      .fetchStatsFilterOptions()
      .then(setOptions)
      .catch((err) => setOptionsError(err.message || "Nu am putut lua filtrele"));
  }, []);

  // cand se schimba filtrele refac toate requesturile
  useEffect(() => {
    // un helper mic sa nu repet
    function load(fetchFn, setState, transform = (x) => x) {
      setState({ data: [], loading: true, error: "" });
      fetchFn(appliedFilters)
        .then((raw) => setState({ data: transform(raw), loading: false, error: "" }))
        .catch((err) =>
          setState({ data: [], loading: false, error: err.message || "Eroare la date" }),
        );
    }

    load(api.fetchPriceTrend, setTrend);
    load(api.fetchPriceDistribution, setDistribution);
    load(api.fetchListingsPerPlatform, setPlatforms);
    load(api.fetchPricePerSqm, setPps, (rows) => rows.slice(0, 15));
  }, [appliedFilters]);

  function handleFilterChange(key, value) {
    setFilters((f) => ({ ...f, [key]: value }));
  }

  function handleApply() {
    setAppliedFilters(filters);
  }

  const inputClass =
    "w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none";

  // 95000 -> 95k (ca sa nu arate urat pe axa)
  const formatShort = (n) => {
    if (n == null) return "";
    if (n >= 1000) return `${Math.round(n / 1000)}k`;
    return String(n);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-7xl p-6">
        <h1 className="mb-4 text-2xl font-semibold text-gray-800">Statistici</h1>

        {/* filtre */}
        <div className="rounded-lg bg-white p-4 shadow-sm">
          {optionsError && (
            <div className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">
              {optionsError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Judet</label>
              <select
                className={inputClass}
                value={filters.county}
                onChange={(e) => handleFilterChange("county", e.target.value)}
                disabled={!options}
              >
                <option value="">Toata Romania</option>
                {options?.counties.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Tranzactie</label>
              <select
                className={inputClass}
                value={filters.transaction_type}
                onChange={(e) => handleFilterChange("transaction_type", e.target.value)}
              >
                <option value="">Toate</option>
                <option value="vanzare">Vanzare</option>
                <option value="inchiriere">Inchiriere</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Tip imobil</label>
              <select
                className={inputClass}
                value={filters.property_type}
                onChange={(e) => handleFilterChange("property_type", e.target.value)}
                disabled={!options}
              >
                <option value="">Toate</option>
                {options?.property_types.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-4">
            <button
              onClick={handleApply}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              Aplica
            </button>
          </div>
        </div>

        {/* grid cu graficele */}
        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* trend preturi pe luni */}
          <ChartCard
            title="Trend pret (media pe luna)"
            loading={trend.loading}
            error={trend.error}
            isEmpty={trend.data.length === 0}
          >
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trend.data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis tickFormatter={formatShort} />
                <Tooltip formatter={(v) => `${v} €`} />
                <Line
                  type="monotone"
                  dataKey="average_price"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* distributia preturilor */}
          <ChartCard
            title="Distributia preturilor"
            loading={distribution.loading}
            error={distribution.error}
            isEmpty={
              distribution.data.length === 0 ||
              distribution.data.every((r) => r.count === 0)
            }
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={distribution.data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* cate anunturi are fiecare platforma */}
          <ChartCard
            title="Anunturi pe platforma"
            loading={platforms.loading}
            error={platforms.error}
            isEmpty={platforms.data.length === 0}
          >
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={platforms.data}
                  dataKey="count"
                  nameKey="platform"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label
                >
                  {platforms.data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* pret pe mp - top 15 orase */}
          <ChartCard
            title="Pret mediu pe mp (top 15 orase)"
            loading={pps.loading}
            error={pps.error}
            isEmpty={pps.data.length === 0}
          >
            <ResponsiveContainer width="100%" height={Math.max(280, pps.data.length * 28)}>
              <BarChart data={pps.data} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={formatShort} />
                {/* interval 0 ca sa se vada toate numele */}
                <YAxis type="category" dataKey="city" width={140} interval={0} />
                <Tooltip formatter={(v) => `${v} €/mp`} />
                <Bar dataKey="price_per_sqm" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      </main>
    </div>
  );
}
