const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
};

document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const foodForm = document.getElementById("foodForm");
  const messageArea = document.getElementById("messageArea");
  const submitBtn = foodForm.querySelector("button[type='submit']");

  if (!localStorage.getItem(STORAGE_KEYS.refreshToken)) {
    redirectToLogin();
    return;
  }

  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-control.html";
  });

  foodForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(messageArea, "", "info");

    const name = document.getElementById("foodName").value.trim();
    const amountRaw = document.getElementById("foodAmount").value.trim();
    const purchaseDate = document.getElementById("purchaseDate").value;
    const expirationDate = document.getElementById("expirationDate").value;

    if (!name || !amountRaw) {
      setMessage(messageArea, "すべての項目を入力してください。", "error");
      return;
    }

    const quantity = Number(amountRaw);
    if (Number.isNaN(quantity) || quantity <= 0) {
      setMessage(messageArea, "数量は1以上の数値で入力してください。", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "送信中...";

    try {
      const token = await ensureValidAccessToken();
      const response = await fetch(`${API_BASE_URL}/ingredients`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name,
          quantity_g: quantity,
          purchase_date: purchaseDate || null,
          expiration_date: expirationDate || null,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 401) {
          clearSession();
          redirectToLogin();
          return;
        }
        throw new Error(data?.detail || "食材の追加に失敗しました。");
      }

      setMessage(
        messageArea,
        `「${data.food_name}（${data.quantity_g}g）」を追加しました。`,
        "success",
      );
      foodForm.reset();
    } catch (error) {
      console.error(error);
      setMessage(messageArea, error.message || "食材の追加に失敗しました。", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "追加";
    }
  });
});

function setMessage(container, text, type) {
  if (!container) return;
  const className = type === "success" ? "success" : type === "error" ? "error" : "info";
  container.innerHTML = text ? `<p class="${className}">${text}</p>` : "";
}

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
