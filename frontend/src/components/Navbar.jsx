// bara de sus (apare dupa login)

import { NavLink } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";
import LogoutButton from "./LogoutButton.jsx";

export default function Navbar() {
  const { user } = useAuth();

  // NavLink imi zice cand e ruta activa ca sa colorez link-ul
  const linkClass = ({ isActive }) =>
    isActive
      ? "text-blue-600 font-semibold"
      : "text-gray-700 hover:text-gray-900";

  return (
    <header className="flex items-center justify-between bg-white px-6 py-4 shadow-sm">
      <nav className="flex items-center gap-6 text-sm">
        <NavLink to="/listings" className={linkClass}>
          Listings
        </NavLink>
        <NavLink to="/statistics" className={linkClass}>
          Statistics
        </NavLink>
        <NavLink to="/predictions" className={linkClass}>
          Predictions
        </NavLink>
      </nav>

      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">
          {user?.username} ({user?.role})
        </span>
        <LogoutButton />
      </div>
    </header>
  );
}
