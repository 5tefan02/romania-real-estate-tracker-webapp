// context pt user - ca sa il am peste tot fara sa dau props prin props

import { createContext, useContext, useEffect, useState } from "react";
import * as api from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // cat timp nu stiu cine e userul, tin loading true
  const [loading, setLoading] = useState(true);

  // la inceput intreb backend-ul cine sunt
  useEffect(() => {
    api
      .fetchMe()
      .then((u) => setUser(u))
      .catch(() => setUser(null)) // 401 inseamna ca nu e logat, e ok
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    const data = await api.login(username, password);
    setUser(data.user);
  }

  async function register(username, email, password) {
    // backend-ul ne logheaza automat dupa register, deci primesc user direct
    const data = await api.register(username, email, password);
    setUser(data.user);
  }

  async function logout() {
    await api.logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
