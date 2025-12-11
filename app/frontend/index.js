const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
  userName: "rr.user_name",
  userEmail: "rr.user_email",
};

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  const message = document.getElementById("message");
  const submitBtn = form.querySelector("button[type='submit']");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.textContent = "";

    const email = form.email.value.trim().toLowerCase();
    const password = form.password.value;

    if (!email || !password) {
      setMessage("メールアドレスとパスワードを入力してください。", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "送信中...";

    try {
      const tokenPayload = await requestLogin(email, password);
      const profile = await fetchCurrentUser(tokenPayload.access_token);
      persistSession(tokenPayload, profile);
      setMessage("ログインに成功しました。", "success");
      setTimeout(() => {
        window.location.href = "home.html";
      }, 600);
    } catch (error) {
      console.error(error);
      setMessage(error.message || "ログインに失敗しました。", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "ログイン";
    }
  });

  function setMessage(text, type) {
    message.textContent = text;
    message.style.color = type === "success" ? "#15803d" : "#dc2626";
  }
});

async function requestLogin(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.detail || "認証に失敗しました。";
    throw new Error(message);
  }

  if (!data.access_token || !data.refresh_token) {
    throw new Error("認証サーバーからの応答が不正です。");
  }
  return data;
}

async function fetchCurrentUser(accessToken) {
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.detail || "ユーザー情報の取得に失敗しました。";
    throw new Error(message);
  }
  return data;
}

function persistSession(tokens, profile) {
  const expiresIn = Number(tokens.expires_in ?? 1800) * 1000;
  const expiresAt = Date.now() + expiresIn;
  localStorage.setItem(STORAGE_KEYS.accessToken, tokens.access_token);
  localStorage.setItem(STORAGE_KEYS.refreshToken, tokens.refresh_token);
  localStorage.setItem(STORAGE_KEYS.accessTokenExpiresAt, String(expiresAt));
  if (profile?.username) {
    localStorage.setItem(STORAGE_KEYS.userName, profile.username);
  }
  if (profile?.email) {
    localStorage.setItem(STORAGE_KEYS.userEmail, profile.email);
  }
}
