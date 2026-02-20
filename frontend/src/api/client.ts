import axios from "axios";

// In production (served from same origin), use relative path.
// In development, point to the local backend server.
const API_BASE = import.meta.env.VITE_API_URL ?? (
  import.meta.env.DEV ? "http://localhost:8000" : ""
);

// Admin API key for write operations (set via VITE_ADMIN_API_KEY env var)
const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY ?? "";

const client = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach API key to all write requests (POST/PUT/DELETE)
client.interceptors.request.use((config) => {
  if (ADMIN_API_KEY && config.method && !["get", "head", "options"].includes(config.method)) {
    config.headers["X-API-Key"] = ADMIN_API_KEY;
  }
  return config;
});

export default client;
