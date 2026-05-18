// wrapper pt paginile de admin
// e asemanator cu ProtectedRoute, doar ca verifica si rolul, nu doar daca e logat
// daca user-ul nu e admin il redirectez la /listings (nu vreau sa-i arat eroare 403)

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";
import Navbar from "./components/Navbar.jsx";

export default function AdminRoute() {
  const { user, loading } = useAuth();

  // cat timp se incarca user-ul (la primul fetch /me) arat un mesaj
  // fara asta s-ar afisa pentru o fractiune de secunda redirect la /login
  // pentru ca user e null initial
  if (loading) {
    return <div className="p-6 text-gray-600">Se incarca...</div>;
  }

  // daca nu e logat -> il duc la login
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // daca e logat dar nu e admin -> il duc la pagina principala
  // (asta acopera si cazul cand rolul s-a schimbat in DB si nu mai e admin)
  if (user.role !== "admin") {
    return <Navigate to="/listings" replace />;
  }

  // daca a trecut de toate verificarile e admin, ii afisez pagina cu navbar
  return (
    <>
      <Navbar />
      <Outlet />
    </>
  );
}
