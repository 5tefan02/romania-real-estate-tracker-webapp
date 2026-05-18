// pagina de login + register cu toggle intre ele

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function Login() {
  // mode = "login" sau "register" - dupa el stiu ce sa afisez si ce sa trimit
  const [mode, setMode] = useState("login");

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();

  // cand schimb modul, curat ce nu mai e relevant ca sa nu raman cu erori vechi
  function switchMode(newMode) {
    setMode(newMode);
    setError("");
    setEmail("");
    setConfirmPassword("");
  }

  async function handleSubmit(event) {
    event.preventDefault(); // altfel face reload
    setError("");

    // verificare locala doar la register: parolele sa coincida
    if (mode === "register" && password !== confirmPassword) {
      setError("Parolele nu coincid");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, email, password);
      }
      navigate("/listings");
    } catch (err) {
      // mesajul vine de la backend
      setError(err.message || "A dat eroare");
    } finally {
      setSubmitting(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg bg-white p-8 shadow"
      >
        {/* toggle-ul intre login si register */}
        <div className="mb-6 flex rounded border border-gray-200 bg-gray-50 p-1">
          <button
            type="button"
            onClick={() => switchMode("login")}
            className={`flex-1 rounded py-1.5 text-sm font-medium ${
              !isRegister
                ? "bg-white text-gray-800 shadow"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Log in
          </button>
          <button
            type="button"
            onClick={() => switchMode("register")}
            className={`flex-1 rounded py-1.5 text-sm font-medium ${
              isRegister
                ? "bg-white text-gray-800 shadow"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Inregistrare
          </button>
        </div>

        <h1 className="mb-6 text-2xl font-semibold text-gray-800">
          {isRegister ? "Cont nou" : "Log in"}
        </h1>

        <label className="mb-2 block text-sm font-medium text-gray-700">
          Username
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoFocus
          className="mb-4 w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
        />

        {/* email apare doar la register */}
        {isRegister && (
          <>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mb-4 w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            />
          </>
        )}

        <label className="mb-2 block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={isRegister ? 6 : undefined}
          className="mb-4 w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
        />

        {/* confirmare parola tot doar la register */}
        {isRegister && (
          <>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Confirma parola
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={6}
              className="mb-4 w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            />
          </>
        )}

        {error && (
          <div className="mb-4 rounded bg-red-50 p-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-blue-600 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting
            ? isRegister
              ? "Se inregistreaza..."
              : "Se logheaza..."
            : isRegister
            ? "Creeaza cont"
            : "Log in"}
        </button>
      </form>
    </div>
  );
}
