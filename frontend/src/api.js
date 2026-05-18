// aici fac request uri la backend (peste fetch)

const API_URL = "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    // include ca sa se trimita cookie-ul (altfel nu merge)
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  // incerc sa iau json si la erori ca sa prind mesajul
  let data = null;
  try {
    data = await response.json();
  } catch {
    // nu are body
  }

  if (!response.ok) {
    const message = (data && data.detail) || `A dat eroare (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

// auth

export function login(username, password) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function register(username, email, password) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

export function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function fetchMe() {
  return request("/api/auth/me", { method: "GET" });
}

// listings

export function fetchFilters() {
  return request("/api/filters", { method: "GET" });
}

// ignor campurile goale cand construiesc url-ul
export function fetchListings(params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== "" && value !== null && value !== undefined) {
      query.append(key, value);
    }
  }
  const qs = query.toString();
  return request(`/api/listings${qs ? `?${qs}` : ""}`, { method: "GET" });
}

// favorites

export function fetchFavorites(params = {}) {
  // aceeasi structura ca fetchListings ca sa pot refolosi ListingCard
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== "" && value !== null && value !== undefined) {
      query.append(key, value);
    }
  }
  const qs = query.toString();
  return request(`/api/favorites${qs ? `?${qs}` : ""}`, { method: "GET" });
}

export function addFavorite(idAnunt) {
  return request(`/api/favorites/${idAnunt}`, { method: "POST" });
}

export function removeFavorite(idAnunt) {
  return request(`/api/favorites/${idAnunt}`, { method: "DELETE" });
}

// criterii notificari pe mail

export function fetchCriterii() {
  // aduce filtrele userului curent (sau null daca nu a salvat inca nimic)
  return request("/api/me/criterii", { method: "GET" });
}

export function saveCriterii(criterii) {
  // salveaza sau updateaza profilul de notificari (upsert pe backend)
  return request("/api/me/criterii", {
    method: "PUT",
    body: JSON.stringify(criterii),
  });
}

// stats

// fac query string-ul sarind peste cele goale
function statsQuery(filters = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== "" && value !== null && value !== undefined) {
      query.append(key, value);
    }
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export function fetchStatsFilterOptions() {
  return request("/api/stats/filter-options", { method: "GET" });
}

export function fetchPriceTrend(filters = {}) {
  return request(`/api/stats/price-trend${statsQuery(filters)}`, { method: "GET" });
}

export function fetchPriceDistribution(filters = {}) {
  return request(`/api/stats/price-distribution${statsQuery(filters)}`, { method: "GET" });
}

export function fetchListingsPerPlatform(filters = {}) {
  return request(`/api/stats/listings-per-platform${statsQuery(filters)}`, { method: "GET" });
}

export function fetchPricePerSqm(filters = {}) {
  return request(`/api/stats/price-per-sqm${statsQuery(filters)}`, { method: "GET" });
}

export function fetchStatusBreakdown(filters = {}) {
  return request(`/api/stats/status-breakdown${statsQuery(filters)}`, { method: "GET" });
}

// ml

export function fetchModelInfo() {
  return request("/api/ml/model-info", { method: "GET" });
}

export function retrainModels() {
  // dureaza ceva pana se antreneaza
  return request("/api/ml/retrain", { method: "POST" });
}

export function fetchMlLocalities() {
  // localitatile pe care le stie modelul (pe judete)
  return request("/api/ml/localities", { method: "GET" });
}

export function predictPrice(input) {
  return request("/api/ml/predict", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// admin

export function fetchAdminUsers() {
  return request("/api/admin/users", { method: "GET" });
}

export function deleteAdminUser(userId) {
  return request(`/api/admin/users/${userId}`, { method: "DELETE" });
}

export function updateAdminListing(idAnunt, payload) {
  return request(`/api/admin/listings/${idAnunt}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteAdminListing(idAnunt) {
  return request(`/api/admin/listings/${idAnunt}`, { method: "DELETE" });
}

export function triggerEtl() {
  return request("/api/admin/etl/run", { method: "POST" });
}

export function fetchAdminStats() {
  return request("/api/admin/stats", { method: "GET" });
}
