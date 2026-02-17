import axios from "axios";

// In production (served from same origin), use relative path.
// In development, point to the local backend server.
const API_BASE = import.meta.env.VITE_API_URL ?? (
  import.meta.env.DEV ? "http://localhost:8000" : ""
);

const client = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

export default client;
