// pagina de admin cu lista de useri si buton de stergere
// admin-ul nu se poate sterge pe el insusi (am pus si pe backend o verificare,
// dar si aici dezactivez butonul ca sa nu para ca merge)

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../../api.js";
import { useAuth } from "../../AuthContext.jsx";

export default function AdminUsers() {
  const { user: currentUser } = useAuth();

  // lista de useri pe care o iau de la backend
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // cand userul apasa pe "Sterge" arat un modal de confirmare
  // tin minte userul intreg, nu doar id-ul, ca sa-i afisez username-ul in modal
  const [showConfirm, setShowConfirm] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);

  // flag separat cat timp se asteapta raspunsul de la backend
  // ca sa dezactivez butonul "Sterge definitiv" sa nu apese de mai multe ori
  const [deleting, setDeleting] = useState(false);

  // la mount iau userii
  useEffect(() => {
    api
      .fetchAdminUsers()
      .then((data) => {
        setUsers(data);
      })
      .catch((err) => {
        setError(err.message || "Eroare la incarcare");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // se apeleaza cand userul apasa "Sterge" pe un rand din tabel
  function openConfirm(user) {
    setUserToDelete(user);
    setShowConfirm(true);
  }

  // se apeleaza cand userul apasa "Anuleaza" sau pe overlay
  function closeConfirm() {
    setShowConfirm(false);
    setUserToDelete(null);
  }

  // se apeleaza cand userul confirma stergerea in modal
  async function handleDelete() {
    if (userToDelete === null) {
      return;
    }
    setDeleting(true);
    try {
      await api.deleteAdminUser(userToDelete.id);
      // dau filter ca sa scot userul sters din lista, fara sa refac fetch
      const newList = users.filter((u) => u.id !== userToDelete.id);
      setUsers(newList);
      closeConfirm();
    } catch (err) {
      setError(err.message || "Eroare la stergere");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <main className="mx-auto max-w-5xl p-6">
        <div className="mb-4">
          <Link to="/admin" className="text-sm text-blue-600 hover:underline">
            {"← Inapoi la dashboard"}
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-gray-800">
            Utilizatori
          </h1>
          <p className="text-sm text-gray-500">
            {users.length} {users.length === 1 ? "utilizator" : "utilizatori"}
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="overflow-hidden rounded-lg bg-white shadow-sm">
          {loading ? (
            <div className="p-6 text-sm text-gray-500">Se incarca...</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Username</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Rol</th>
                  <th className="px-4 py-3">Creat</th>
                  <th className="px-4 py-3 text-right">Actiuni</th>
                </tr>
              </thead>
              <tbody className="text-gray-700">
                {users.map((u) => {
                  // verific daca userul din rand este chiar cel logat
                  // (folosesc isSelf in mai multe locuri mai jos)
                  let isSelf = false;
                  if (currentUser && u.id === currentUser.id) {
                    isSelf = true;
                  }

                  // formatez data de creare in format romanesc (dd.mm.yyyy)
                  // backend-ul trimite ISO; daca lipseste pun "-"
                  let createdFormatted = "-";
                  if (u.created_at) {
                    const d = new Date(u.created_at);
                    createdFormatted = d.toLocaleDateString("ro-RO");
                  }

                  // aleg cum sa fie clasa pt eticheta de rol
                  // admin = mov, user = gri
                  let roleClass = "rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600";
                  if (u.role === "admin") {
                    roleClass = "rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700";
                  }

                  return (
                    <tr key={u.id} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-500">{u.id}</td>
                      <td className="px-4 py-3 font-medium text-gray-800">
                        {u.username}
                        {isSelf && (
                          <span className="ml-2 rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
                            tu
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">{u.email}</td>
                      <td className="px-4 py-3">
                        <span className={roleClass}>{u.role}</span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{createdFormatted}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          disabled={isSelf}
                          onClick={() => openConfirm(u)}
                          className="rounded bg-red-50 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
                          title={isSelf ? "Nu te poti sterge pe tine insuti" : "Sterge utilizatorul"}
                        >
                          Sterge
                        </button>
                      </td>
                    </tr>
                  );
                })}

                {/* daca nu sunt useri afisez o linie cu mesaj */}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                      Nu exista utilizatori.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {/* modal de confirmare la stergere
          arat doar daca showConfirm e true si am un user de sters in state */}
      {showConfirm && userToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="mb-2 text-lg font-semibold text-gray-800">
              Confirmare stergere
            </h3>
            <p className="mb-4 text-sm text-gray-600">
              Sigur stergi userul <strong>{userToDelete.username}</strong> (
              {userToDelete.email})?
              <br />
              Se sterg si toate favoritele, criteriile de notificari si
              istoricul de mailuri trimise pentru el. Actiunea nu se poate
              undo.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={closeConfirm}
                disabled={deleting}
                className="rounded bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
              >
                Anuleaza
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="rounded bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:bg-gray-400"
              >
                {deleting ? "Se sterge..." : "Sterge definitiv"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
