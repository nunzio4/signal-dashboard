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

/**
 * Get the admin API key from sessionStorage.
 * If not set, prompt the user for it (happens once per browser session).
 */
function getAdminKey(): string {
  let key = sessionStorage.getItem("admin_api_key");
  if (!key) {
    key = window.prompt("Admin API key required for this action:") ?? "";
    if (key) {
      sessionStorage.setItem("admin_api_key", key);
    }
  }
  return key;
}

// Attach API key to all write requests (POST/PUT/DELETE)
client.interceptors.request.use((config) => {
  if (config.method && !["get", "head", "options"].includes(config.method)) {
    const key = getAdminKey();
    if (key) {
      config.headers["X-API-Key"] = key;
    }
  }
  return config;
});

// If a 403 comes back, clear the stored key so the user gets re-prompted
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 403) {
      sessionStorage.removeItem("admin_api_key");
    }
    return Promise.reject(error);
  },
);

export default client;
