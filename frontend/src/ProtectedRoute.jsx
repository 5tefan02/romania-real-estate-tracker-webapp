// wrapper pt paginile care cer login

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";
import Navbar from "./components/Navbar.jsx";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-6 text-gray-600">Se incarca...</div>;
  }

  if (!user) {
    // replace ca sa nu se intoarca la pagina protejata cu back
    return <Navigate to="/login" replace />;
  }

  // pe paginile protejate pun mereu navbar sus
  return (
    <>
      <Navbar />
      <Outlet />
    </>
  );
}
