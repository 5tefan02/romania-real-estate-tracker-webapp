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

  // pt favorite vreau styling un pic diferit ca sa iasa in evidenta
  const favoriteClass = ({ isActive }) =>
    isActive
      ? "flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1.5 text-red-600 font-semibold"
      : "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-gray-600 hover:bg-gray-100";

  return (
    <header className="flex items-center justify-between bg-white px-6 py-4 shadow-sm">
      {/* stanga: logo / numele aplicatiei */}
      <NavLink to="/listings" className="text-2xl font-bold tracking-tight text-blue-600">
        Evesta
      </NavLink>

      {/* mijloc: navigare principala */}
      <nav className="flex items-center gap-6 text-sm">
        <NavLink to="/listings" className={linkClass}>
          Anunturi
        </NavLink>
        <NavLink to="/statistics" className={linkClass}>
          Statistici
        </NavLink>
        <NavLink to="/predictions" className={linkClass}>
          Predictii
        </NavLink>
        {/* link-ul de admin apare doar pentru conturile cu rol admin */}
        {user?.role === "admin" && (
          <NavLink to="/admin" className={linkClass}>
            Admin
          </NavLink>
        )}
      </nav>

      {/* dreapta: favorite + user + logout */}
      <div className="flex items-center gap-4 text-sm">
        <NavLink to="/favorites" className={favoriteClass}>
          <span className="text-base leading-none">{"\u2665"}</span>
          <span>Favorite</span>
        </NavLink>

        {/* separator vertical subtire intre favorite si zona de user */}
        <span className="h-6 w-px bg-gray-200" />

        {/* numele userului e link catre pagina de profil
            (de acolo se seteaza filtrele de notificari) */}
        <NavLink
          to="/profile"
          className={({ isActive }) =>
            isActive
              ? "text-blue-600 font-semibold"
              : "text-gray-600 hover:text-gray-900"
          }
        >
          {user?.username}{" "}
          <span className="text-xs text-gray-400">({user?.role})</span>
        </NavLink>
        <LogoutButton />
      </div>
    </header>
  );
}
