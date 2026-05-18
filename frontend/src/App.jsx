// componenta principala - auth + routing

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthContext.jsx";
import ProtectedRoute from "./ProtectedRoute.jsx";
import AdminRoute from "./AdminRoute.jsx";
import Login from "./pages/Login.jsx";
import Listings from "./pages/Listings.jsx";
import Favorites from "./pages/Favorites.jsx";
import Statistics from "./pages/Statistics.jsx";
import Predictions from "./pages/Predictions.jsx";
import Profile from "./pages/Profile.jsx";
import AdminDashboard from "./pages/admin/AdminDashboard.jsx";
import AdminUsers from "./pages/admin/AdminUsers.jsx";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* rute care cer login */}
          <Route element={<ProtectedRoute />}>
            <Route path="/listings" element={<Listings />} />
            <Route path="/favorites" element={<Favorites />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/profile" element={<Profile />} />
          </Route>

          {/* rute care cer rol admin */}
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
          </Route>

          {/* orice altceva duce la listings (sau login daca nu e logat) */}
          <Route path="*" element={<Navigate to="/listings" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
