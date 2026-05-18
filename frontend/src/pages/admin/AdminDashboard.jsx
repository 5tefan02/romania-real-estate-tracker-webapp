// pagina de dashboard admin
// afiseaza cateva numere mari (KPI-uri) sus, apoi grafice mai jos
// am si un buton de link catre /admin/users pentru gestionarea conturilor
//
// toate datele vin dintr-un singur fetch GET /api/admin/stats
// (am preferat un endpoint mare in loc de 7 mici - se face un singur request)

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import * as api from "../../api.js";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // la mount fac fetch o singura data
  useEffect(() => {
    api
      .fetchAdminStats()
      .then((data) => {
        setStats(data);
      })
      .catch((err) => {
        setError(err.message || "Eroare la incarcare");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // formatez un numar mare cu separator de mii (1234 -> "1.234")
  function formatNumber(value) {
    if (value === null || value === undefined) {
      return "-";
    }
    return new Intl.NumberFormat("ro-RO").format(value);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <main className="mx-auto max-w-6xl p-6 text-sm text-gray-500">
          Se incarca dashboard-ul...
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100">
        <main className="mx-auto max-w-6xl p-6">
          <div className="rounded bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-6xl space-y-6 p-6">
        {/* header cu titlu si link catre useri */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">
              Dashboard
            </h1>
            <p className="text-sm text-gray-600">
              Statistici generale despre platforma.
            </p>
          </div>
          <Link
            to="/admin/users"
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Gestioneaza utilizatori
          </Link>
        </div>

        {/* carduri cu numere mari (KPI-uri) */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg bg-white p-5 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-gray-500">
              Utilizatori
            </div>
            <div className="mt-2 text-3xl font-semibold text-gray-800">
              {formatNumber(stats.users_total)}
            </div>
            <div className="mt-1 text-xs text-gray-500">
              {formatNumber(stats.users_active_profile)} cu profil notificari
              activ
            </div>
          </div>

          <div className="rounded-lg bg-white p-5 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-gray-500">
              Anunturi
            </div>
            <div className="mt-2 text-3xl font-semibold text-gray-800">
              {formatNumber(stats.listings_total)}
            </div>
            <div className="mt-1 text-xs text-gray-500">total in baza de date</div>
          </div>

          <div className="rounded-lg bg-white p-5 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-gray-500">
              Anunturi noi azi
            </div>
            <div className="mt-2 text-3xl font-semibold text-gray-800">
              {formatNumber(stats.listings_new_today)}
            </div>
            <div className="mt-1 text-xs text-gray-500">
              {formatNumber(stats.listings_new_week)} in ultimele 7 zile
            </div>
          </div>

          <div className="rounded-lg bg-white p-5 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-gray-500">
              Mailuri trimise (7 zile)
            </div>
            <div className="mt-2 text-3xl font-semibold text-gray-800">
              {/* sumez toate cele 7 zile pt total saptamana */}
              {formatNumber(
                stats.emails_last_7_days.reduce((acc, d) => acc + d.count, 0),
              )}
            </div>
            <div className="mt-1 text-xs text-gray-500">
              detalii in graficul de mai jos
            </div>
          </div>
        </div>

        {/* line chart - mailuri ultimele 7 zile */}
        <div className="rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-gray-800">
            Mailuri trimise in ultimele 7 zile
          </h2>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={stats.emails_last_7_days}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="data" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#10b981"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </main>
    </div>
  );
}
