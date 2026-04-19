// butonul de logout

import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function LogoutButton() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  async function handleClick() {
    await logout();
    navigate("/login");
  }

  return (
    <button
      onClick={handleClick}
      className="rounded bg-gray-800 px-3 py-1.5 text-sm text-white hover:bg-gray-700"
    >
      Log out
    </button>
  );
}
