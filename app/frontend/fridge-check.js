const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
};

document.addEventListener("DOMContentLoaded", () => {
  const foodList = document.getElementById("foodList");

  if (!localStorage.getItem(STORAGE_KEYS.refreshToken)) {
    redirectToLogin();
    return;
  }

  loadFoods();

  async function loadFoods() {
    foodList.innerHTML = `<tr><td colspan="5">読み込み中...</td></tr>`;
    try {
      const token = await ensureValidAccessToken();
      const response = await fetch(`${API_BASE_URL}/ingredients`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        throw new Error(data?.detail || "食材一覧の取得に失敗しました。");
      }

      const items = data?.ingredients ?? [];
      if (!items.length) {
        foodList.innerHTML = `<tr><td colspan="5">冷蔵庫に食材が登録されていません。</td></tr>`;
        return;
      }

      foodList.innerHTML = items
        .map(
          (item) => `
            <tr>
              <td>${item.food_name}</td>
              <td>${item.quantity_g} g</td>
              <td>${item.purchase_date || "-"}</td>
              <td>${item.expiration_date || "-"}</td>
            </tr>
          `,
        )
        .join("");
    } catch (error) {
      console.error("データ取得エラー", error);
      foodList.innerHTML = `<tr><td colspan="5">データの取得に失敗しました。</td></tr>`;
    }
  }
});

function redirectToLogin() {
  window.location.href = "index.html";
}

function clearSession() {
  Object.values(STORAGE_KEYS).forEach((key) => {
    if (typeof key === "string") {
      localStorage.removeItem(key);
    }
  });
}

async function ensureValidAccessToken() {
  const accessKey = STORAGE_KEYS.accessToken;
  const refreshKey = STORAGE_KEYS.refreshToken;
  const expiresKey = STORAGE_KEYS.accessTokenExpiresAt;
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
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) {
    clearSession();
    throw new Error(data?.detail || "トークンの更新に失敗しました。");
  }

  const accessKey = STORAGE_KEYS.accessToken;
  const expiresKey = STORAGE_KEYS.accessTokenExpiresAt;
  const expiresInMs = Number(data.expires_in ?? 1800) * 1000;
  localStorage.setItem(accessKey, data.access_token);
  localStorage.setItem(expiresKey, String(Date.now() + expiresInMs));
  return data.access_token;
}
