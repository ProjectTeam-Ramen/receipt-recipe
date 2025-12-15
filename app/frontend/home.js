const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
  userName: "rr.user_name",
  userEmail: "rr.user_email",
};

document.addEventListener("DOMContentLoaded", () => {
  const logoutBtn = document.getElementById("logoutBtn");
  const recipeBtn = document.getElementById("recipeBtn");
  const fridgeBtn = document.getElementById("fridgeBtn");
  const resolverBtn = document.getElementById("resolverBtn");
  const welcomeMsg = document.getElementById("welcomeMsg");
  const statusMsg = document.getElementById("statusMessage");

  if (!localStorage.getItem(STORAGE_KEYS.refreshToken)) {
    redirectToLogin();
    return;
  }

  recipeBtn?.addEventListener("click", () => (window.location.href = "recipe.html"));
  fridgeBtn?.addEventListener("click", () => (window.location.href = "fridge-home.html"));
  resolverBtn?.addEventListener("click", () => (window.location.href = "ingredient-resolver.html"));
  logoutBtn?.addEventListener("click", () => handleLogout());

  loadProfile().catch((error) => {
    console.error(error);
    setStatus(error.message || "セッションが無効です。", "error");
    clearSession();
    setTimeout(() => redirectToLogin(), 1000);
  });

  async function loadProfile() {
    setStatus("プロフィールを取得しています...", "info");
    const token = await ensureValidAccessToken();
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data?.detail || "ユーザー情報の取得に失敗しました。");
    }
    localStorage.setItem(STORAGE_KEYS.userName, data.username || "");
    localStorage.setItem(STORAGE_KEYS.userEmail, data.email || "");
    welcomeMsg.textContent = `${data.username ?? "ユーザー"} さんでログイン中です。`;
    setStatus("", "info");
  }

  async function handleLogout() {
    const refreshToken = localStorage.getItem(STORAGE_KEYS.refreshToken);
    clearSession();
    try {
      if (refreshToken) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      }
    } catch (error) {
      console.warn("Failed to notify server about logout", error);
    }
    redirectToLogin();
  }

  function setStatus(text, type) {
    if (!statusMsg) return;
    statusMsg.textContent = text || "";
    const colors = {
      info: "#4b5563",
      success: "#15803d",
      error: "#dc2626",
    };
    statusMsg.style.color = colors[type] || colors.info;
  }
});

function clearSession() {
  const keys = window.APP_CONFIG?.storageKeys ?? {};
  Object.values(keys).forEach((key) => {
    if (typeof key === "string") {
      localStorage.removeItem(key);
    }
  });
}

async function ensureValidAccessToken() {
  const cfg = window.APP_CONFIG?.storageKeys ?? {};
  const accessKey = cfg.accessToken || "rr.access_token";
  const refreshKey = cfg.refreshToken || "rr.refresh_token";
  const expiresKey = cfg.accessTokenExpiresAt || "rr.access_token_expires_at";

  const expiresAt = Number(localStorage.getItem(expiresKey) || 0);
  const refreshToken = localStorage.getItem(refreshKey);
  let accessToken = localStorage.getItem(accessKey);

  if (accessToken && Date.now() < expiresAt - 5000) {
    return accessToken;
  }

  if (!refreshToken) {
    throw new Error("ログインの有効期限が切れています。");
  }

  return refreshAccessToken(refreshToken);
}

async function refreshAccessToken(refreshToken) {
  const apiBase = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
  const response = await fetch(`${apiBase}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) {
    throw new Error(data?.detail || "トークンの更新に失敗しました。");
  }

  const cfg = window.APP_CONFIG?.storageKeys ?? {};
  const accessKey = cfg.accessToken || "rr.access_token";
  const expiresKey = cfg.accessTokenExpiresAt || "rr.access_token_expires_at";
  const expiresIn = Number(data.expires_in ?? 1800) * 1000;
  const expiresAt = Date.now() + expiresIn;
  localStorage.setItem(accessKey, data.access_token);
  localStorage.setItem(expiresKey, String(expiresAt));
  return data.access_token;
}

function redirectToLogin() {
  window.location.href = "index.html";
}
