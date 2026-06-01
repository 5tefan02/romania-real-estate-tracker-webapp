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
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import * as api from "../api.js";

// filtre goale (default tranzactie = vanzare, tip imobil = Apartament)
// amestecul de categorii strica statisticile - chiriile sunt in sute de EUR vs
// vanzarile in zeci de mii, iar apartamentele/casele/terenurile au scari de
// suprafata si pret complet diferite
const EMPTY_FILTERS = {
  county: "",
  transaction_type: "vanzare",
  property_type: "Apartament",
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
  const [pps, setPps] = useState({ data: [], loading: true, error: "" });
  const [rooms, setRooms] = useState({ data: [], loading: true, error: "" });
  const [period, setPeriod] = useState({ data: [], loading: true, error: "" });
  const [compartment, setCompartment] = useState({ data: [], loading: true, error: "" });
  const [topCities, setTopCities] = useState({ data: [], loading: true, error: "" });
  const [surfaceDist, setSurfaceDist] = useState({ data: [], loading: true, error: "" });
  const [priceChanges, setPriceChanges] = useState({ data: null, loading: true, error: "" });
  const [lifetime, setLifetime] = useState({ data: null, loading: true, error: "" });
  const [topBottom, setTopBottom] = useState({ data: null, loading: true, error: "" });
  const [scatter, setScatter] = useState({ data: [], loading: true, error: "" });

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
    // initial e [] default (lista), dar pt endpoint-urile care intorc obiect pun null
    function load(fetchFn, setState, transform = (x) => x, initial = []) {
      setState({ data: initial, loading: true, error: "" });
      fetchFn(appliedFilters)
        .then((raw) => setState({ data: transform(raw), loading: false, error: "" }))
        .catch((err) =>
          setState({ data: initial, loading: false, error: err.message || "Eroare la date" }),
        );
    }

    load(api.fetchPriceTrend, setTrend);
    load(api.fetchPriceDistribution, setDistribution);
    load(api.fetchPricePerSqm, setPps, (rows) => rows.slice(0, 15));
    load(api.fetchRoomsDistribution, setRooms);
    load(api.fetchPeriodDistribution, setPeriod);
    load(api.fetchCompartmentDistribution, setCompartment);
    load(api.fetchTopCities, setTopCities);
    load(api.fetchSurfaceDistribution, setSurfaceDist);
    load(api.fetchPriceChanges, setPriceChanges, (x) => x, null);
    load(api.fetchListingLifetime, setLifetime, (x) => x, null);
    load(api.fetchTopBottomCounties, setTopBottom, (x) => x, null);
    load(api.fetchSurfaceVsPrice, setScatter);
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

        {/* secțiuni cu grafice grupate logic */}
        <div className="mt-6 space-y-8">

          {/* --- 1. PRETURI --- */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-gray-700">Preturi</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

              {/* trend preturi pe saptamani - full width */}
              <div className="lg:col-span-2">
                <ChartCard
                  title="Trend pret (media pe saptamana)"
                  loading={trend.loading}
                  error={trend.error}
                  isEmpty={trend.data.length === 0}
                >
                  <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={trend.data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="week" />
                      <YAxis tickFormatter={formatShort} />
                      <Tooltip formatter={(v) => `${v} €`} />
                      <Line
                        type="monotone"
                        dataKey="pret mediu"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

              {/* distributia preturilor - full width pt mai multe bare */}
              <div className="lg:col-span-2">
                <ChartCard
                  title="Distributia preturilor"
                  loading={distribution.loading}
                  error={distribution.error}
                  isEmpty={
                    distribution.data.length === 0 ||
                    distribution.data.every((r) => r.count === 0)
                  }
                >
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={distribution.data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="range" angle={-30} textAnchor="end" height={60} />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="count" fill="#10b981" />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

            </div>
          </section>

          {/* --- 2. PROFILUL ANUNTURILOR --- */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-gray-700">Profilul anunturilor</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

              {/* distributia pe nr de camere */}
              <ChartCard
                title="Distributia pe nr de camere"
                loading={rooms.loading}
                error={rooms.error}
                isEmpty={rooms.data.length === 0 || rooms.data.every((r) => r.count === 0)}
              >
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={rooms.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="rooms" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#8b5cf6" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              {/* distributia pe perioada constructiei */}
              <ChartCard
                title="Distributia pe perioada constructiei"
                loading={period.loading}
                error={period.error}
                isEmpty={period.data.length === 0}
              >
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={period.data}
                      dataKey="count"
                      nameKey="period"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label
                    >
                      {period.data.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>

              {/* distributia pe compartimentare */}
              <ChartCard
                title="Distributia pe compartimentare"
                loading={compartment.loading}
                error={compartment.error}
                isEmpty={compartment.data.length === 0}
              >
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={compartment.data}
                      dataKey="count"
                      nameKey="compartment"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label
                    >
                      {compartment.data.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>

              {/* distributia pe suprafata (mp) */}
              <ChartCard
                title="Distributia pe suprafata (mp)"
                loading={surfaceDist.loading}
                error={surfaceDist.error}
                isEmpty={
                  surfaceDist.data.length === 0 ||
                  surfaceDist.data.every((r) => r.count === 0)
                }
              >
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={surfaceDist.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="range" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#ec4899" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

            </div>
          </section>

          {/* --- 3. GEOGRAFIE --- */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-gray-700">Geografie</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

              {/* top 10 orase/zone (include sectoarele) */}
              <ChartCard
                title="Top 10 orase/zone (anunturi active)"
                loading={topCities.loading}
                error={topCities.error}
                isEmpty={topCities.data.length === 0}
              >
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(280, topCities.data.length * 28)}
                >
                  <BarChart data={topCities.data} layout="vertical" margin={{ left: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="city" width={140} interval={0} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#10b981" />
                  </BarChart>
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
                    <YAxis type="category" dataKey="city" width={140} interval={0} />
                    <Tooltip formatter={(v) => `${v} €/mp`} />
                    <Bar dataKey="price_per_sqm" fill="#f59e0b" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              {/* top 5 judete - cele mai scumpe */}
              <ChartCard
                title="Top 5 judete (cele mai scumpe)"
                loading={topBottom.loading}
                error={topBottom.error}
                isEmpty={!topBottom.data || topBottom.data.top.length === 0}
              >
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={topBottom.data?.top || []}
                    layout="vertical"
                    margin={{ left: 40 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tickFormatter={formatShort} />
                    <YAxis type="category" dataKey="county" width={140} interval={0} />
                    <Tooltip formatter={(v) => `${v} €`} />
                    <Bar dataKey="avg_price" fill="#ef4444" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              {/* bottom 5 judete - cele mai ieftine */}
              <ChartCard
                title="Bottom 5 judete (cele mai ieftine)"
                loading={topBottom.loading}
                error={topBottom.error}
                isEmpty={!topBottom.data || topBottom.data.bottom.length === 0}
              >
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={topBottom.data?.bottom || []}
                    layout="vertical"
                    margin={{ left: 40 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tickFormatter={formatShort} />
                    <YAxis type="category" dataKey="county" width={140} interval={0} />
                    <Tooltip formatter={(v) => `${v} €`} />
                    <Bar dataKey="avg_price" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

            </div>
          </section>

          {/* --- 4. CORELATII --- */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-gray-700">Corelatii</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

              {/* scatter suprafata vs pret - full width */}
              <div className="lg:col-span-2">
                <ChartCard
                  title="Suprafata vs pret (esantion)"
                  loading={scatter.loading}
                  error={scatter.error}
                  isEmpty={scatter.data.length === 0}
                >
                  <ResponsiveContainer width="100%" height={320}>
                    <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        type="number"
                        dataKey="surface"
                        name="Suprafata"
                        unit=" mp"
                      />
                      <YAxis
                        type="number"
                        dataKey="price"
                        name="Pret"
                        tickFormatter={formatShort}
                      />
                      <ZAxis range={[15, 15]} />
                      <Tooltip
                        cursor={{ strokeDasharray: "3 3" }}
                        formatter={(v, name) =>
                          name === "Pret" ? `${v} €` : `${v}`
                        }
                      />
                      <Scatter data={scatter.data} fill="#3b82f6" fillOpacity={0.5} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

            </div>
          </section>

          {/* --- 5. DINAMICA PIETEI --- */}
          <section>
            <h2 className="mb-3 text-lg font-semibold text-gray-700">Dinamica pietei</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

              {/* modificari de pret (KPI) */}
              <ChartCard
                title="Modificari de pret"
                loading={priceChanges.loading}
                error={priceChanges.error}
                isEmpty={!priceChanges.data || priceChanges.data.total_anunturi === 0}
              >
                <div className="flex h-64 flex-col justify-center gap-3 px-2">
                  <div className="text-center">
                    <div className="text-4xl font-bold text-blue-600">
                      {priceChanges.data?.procent_anunturi_cu_modificari ?? 0}%
                    </div>
                    <div className="text-xs text-gray-500">
                      din anunturi au avut cel putin o modificare de pret
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="rounded bg-red-50 p-3 text-center">
                      <div className="text-xs uppercase text-gray-600">Scaderi</div>
                      <div className="text-xl font-semibold text-red-600">
                        {priceChanges.data?.scaderi ?? 0}
                      </div>
                      <div className="text-xs text-gray-500">
                        media {priceChanges.data?.avg_scadere_pct ?? 0}%
                      </div>
                    </div>
                    <div className="rounded bg-green-50 p-3 text-center">
                      <div className="text-xs uppercase text-gray-600">Cresteri</div>
                      <div className="text-xl font-semibold text-green-600">
                        {priceChanges.data?.cresteri ?? 0}
                      </div>
                      <div className="text-xs text-gray-500">
                        media +{priceChanges.data?.avg_crestere_pct ?? 0}%
                      </div>
                    </div>
                  </div>
                </div>
              </ChartCard>

              {/* timpul mediu activ */}
              <ChartCard
                title="Timpul mediu de viata al unui anunt"
                loading={lifetime.loading}
                error={lifetime.error}
                isEmpty={!lifetime.data || lifetime.data.count === 0}
              >
                <div className="flex h-64 flex-col items-center justify-center gap-2">
                  <div className="text-6xl font-bold text-indigo-600">
                    {lifetime.data?.avg_days ?? 0}
                  </div>
                  <div className="text-base text-gray-600">zile in medie</div>
                  <div className="mt-3 text-xs text-gray-500">
                    (calculat pe {lifetime.data?.count ?? 0} anunturi inactivate)
                  </div>
                </div>
              </ChartCard>

            </div>
          </section>

        </div>
      </main>
    </div>
  );
}
