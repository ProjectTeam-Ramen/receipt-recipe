const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
    accessToken: "rr.access_token",
    refreshToken: "rr.refresh_token",
    accessTokenExpiresAt: "rr.access_token_expires_at",
};

const MAX_HISTORY = 5;
const historyEntries = [];

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("resolveForm");
    const rawTextInput = document.getElementById("rawText");
    const topKInput = document.getElementById("topK");
    const forceRefreshInput = document.getElementById("forceRefresh");
    const statusMessage = document.getElementById("statusMessage");
    const submitBtn = document.getElementById("submitBtn");
    const resultSection = document.getElementById("resultSection");
    const normalizedText = document.getElementById("normalizedText");
    const resolvedFood = document.getElementById("resolvedFood");
    const resolvedFoodId = document.getElementById("resolvedFoodId");
    const resolvedConfidence = document.getElementById("resolvedConfidence");
    const resolvedSource = document.getElementById("resolvedSource");
    const metadataOutput = document.getElementById("metadataOutput");
    const historyList = document.getElementById("historyList");
    const backBtn = document.getElementById("backBtn");

    if (!localStorage.getItem(STORAGE_KEYS.refreshToken)) {
        redirectToLogin();
        return;
    }

    backBtn?.addEventListener("click", () => (window.location.href = "home.html"));

    form?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const rawText = rawTextInput.value.trim();
        const topK = Number(topKInput.value) || 5;
        const forceRefresh = Boolean(forceRefreshInput.checked);

        if (!rawText) {
            setStatus("文字列を入力してください。", "error");
            return;
        }
        if (topK < 1 || topK > 10) {
            setStatus("top_k は 1 〜 10 の範囲で指定してください。", "error");
            return;
        }

        submitBtn.disabled = true;
        setStatus("抽象化リクエストを送信しています...", "info");

        try {
            const token = await ensureValidAccessToken();
            const response = await fetch(`${API_BASE_URL}/ingredient-abstractions/resolve`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ raw_text: rawText, force_refresh: forceRefresh, top_k: topK }),
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                handleAuthError(response.status);
                throw new Error(data?.detail || "抽象化に失敗しました。");
            }

            renderResult({
                rawText,
                request: { topK, forceRefresh },
                payload: data,
            });
            updateHistory({
                rawText,
                normalizedText: data.normalized_text,
                resolved: data.resolved_food_name,
                cached: data.cached,
                timestamp: new Date(),
            });
            toggleResult(true);
            setStatus(data.cached ? "キャッシュから返却しました。" : "新しい推論結果を保存しました。", "success");
        } catch (error) {
            console.error(error);
            const message = normalizeErrorMessage(error);
            setStatus(message, "error");
            toggleResult(false);
        } finally {
            submitBtn.disabled = false;
        }
    });

    function toggleResult(show) {
        if (!resultSection) return;
        resultSection.classList.toggle("hidden", !show);
    }

    function setStatus(text, type = "info") {
        if (!statusMessage) return;
        statusMessage.textContent = text || "";
        statusMessage.className = `resolver-status ${type}`;
    }

    function renderResult({ payload }) {
        if (!payload) return;
        normalizedText.textContent = payload.normalized_text || "-";
        resolvedFood.textContent = payload.resolved_food_name || "-";
        resolvedFoodId.textContent = payload.food_id ?? "-";
        resolvedConfidence.textContent = formatConfidence(payload.confidence);
        resolvedSource.textContent = `${payload.source || "-"} / ${payload.cached ? "cached" : "fresh"}`;
        metadataOutput.textContent = JSON.stringify(payload.metadata ?? {}, null, 2);
    }

    function updateHistory(entry) {
        historyEntries.unshift(entry);
        if (historyEntries.length > MAX_HISTORY) {
            historyEntries.pop();
        }
        renderHistory();
    }

    function renderHistory() {
        if (!historyList) return;
        if (!historyEntries.length) {
            historyList.innerHTML = '<li class="muted">まだ履歴がありません。</li>';
            return;
        }
        historyList.innerHTML = historyEntries
            .map((entry) => {
                const time = entry.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                return `<li><strong>${time}</strong> raw:"${escapeHtml(entry.rawText)}" → <em>${entry.resolved || "-"}</em> (${entry.cached ? "cache" : "predict"})</li>`;
            })
            .join("");
    }

    renderHistory();
});

function escapeHtml(value = "") {
    const span = document.createElement("span");
    span.textContent = value;
    return span.innerHTML;
}

function normalizeErrorMessage(error) {
    if (!error) return "抽象化に失敗しました。";
    if (error instanceof TypeError && /Failed to fetch/i.test(error.message)) {
        return "API サーバーに接続できませんでした。バックエンドが起動しているか、ネットワーク/HTTPS設定をご確認ください。";
    }
    return error.message || "抽象化に失敗しました。";
}

function formatConfidence(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return "-";
    }
    return `${Math.round(value * 100)}%`;
}

function handleAuthError(status) {
    if (status === 401) {
        clearSession();
        redirectToLogin();
    }
}

function clearSession() {
    Object.values(STORAGE_KEYS).forEach((key) => {
        if (typeof key === "string") {
            localStorage.removeItem(key);
        }
    });
}

async function ensureValidAccessToken() {
    const accessKey = STORAGE_KEYS.accessToken || "rr.access_token";
    const refreshKey = STORAGE_KEYS.refreshToken || "rr.refresh_token";
    const expiresKey = STORAGE_KEYS.accessTokenExpiresAt || "rr.access_token_expires_at";

    const expiresAt = Number(localStorage.getItem(expiresKey) || 0);
    const refreshToken = localStorage.getItem(refreshKey);
    const currentToken = localStorage.getItem(accessKey);

    if (currentToken && Date.now() < expiresAt - 5000) {
        return currentToken;
    }
    if (!refreshToken) {
        throw new Error("ログインの有効期限が切れています。再度ログインしてください。");
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

    const accessKey = STORAGE_KEYS.accessToken || "rr.access_token";
    const expiresKey = STORAGE_KEYS.accessTokenExpiresAt || "rr.access_token_expires_at";
    const expiresIn = Number(data.expires_in ?? 1800) * 1000;
    const expiresAt = Date.now() + expiresIn;
    localStorage.setItem(accessKey, data.access_token);
    localStorage.setItem(expiresKey, String(expiresAt));
    return data.access_token;
}

function redirectToLogin() {
    window.location.href = "index.html";
}
