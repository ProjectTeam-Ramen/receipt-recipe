const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
    accessToken: "rr.access_token",
    refreshToken: "rr.refresh_token",
    accessTokenExpiresAt: "rr.access_token_expires_at",
};

let currentRecipeId = null;

document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    currentRecipeId = params.get("id");
    const messageEl = document.getElementById("cookMessage");

    if (!currentRecipeId) {
        setStatusMessage("レシピIDが指定されていません。レシピ一覧から選択してください。", true);
        return;
    }

    const backBtn = document.getElementById("backToList");
    if (backBtn) {
        backBtn.addEventListener("click", () => {
            window.location.href = "recipe.html";
        });
    }

    const cookForm = document.getElementById("cookForm");
    if (cookForm) {
        cookForm.addEventListener("submit", async (evt) => {
            evt.preventDefault();
            await handleCookAction();
        });
    }

    loadRecipeDetail().catch((err) => {
        console.error("detail load failed", err);
        setStatusMessage(err?.message ?? "レシピ情報の取得に失敗しました。", true);
    });
});

async function loadRecipeDetail() {
    setStatusMessage("レシピ情報を読み込んでいます…", false);
    const headers = {};
    let token = null;
    try {
        token = await ensureValidAccessToken();
    } catch (err) {
        console.debug("token refresh skipped", err);
    }
    if (token) headers.Authorization = `Bearer ${token}`;

    const resp = await fetch(`${API_BASE_URL}/recipes/${currentRecipeId}`, { headers });
    if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body?.detail ?? `レシピ取得に失敗しました (${resp.status})`);
    }
    const detail = await resp.json();
    renderRecipeDetail(detail);
    setStatusMessage("", false);
}

function renderRecipeDetail(detail) {
    const titleEl = document.getElementById("recipeTitle");
    const metaEl = document.getElementById("recipeMeta");
    const descEl = document.getElementById("recipeDescription");
    const bodyEl = document.getElementById("ingredientBody");
    const instructionsEl = document.getElementById("recipeInstructions");
    if (!bodyEl) {
        return;
    }

    if (titleEl) titleEl.textContent = detail.recipe_name || "名称不明のレシピ";
    const metaParts = [];
    if (typeof detail.cooking_time === "number") metaParts.push(`調理時間: ${detail.cooking_time}分`);
    if (typeof detail.calories === "number") metaParts.push(`約${detail.calories}kcal`);
    if (metaEl) metaEl.textContent = metaParts.length ? metaParts.join(" / ") : "";
    if (descEl) descEl.textContent = detail.description || "";
    if (instructionsEl) {
        const instructionsText = typeof detail.instructions === "string" && detail.instructions.trim()
            ? detail.instructions.trim()
            : "作り方の情報がありません。";
        instructionsEl.textContent = instructionsText;
        instructionsEl.classList.toggle("muted", instructionsText === "作り方の情報がありません。");
    }

    if (!Array.isArray(detail.ingredients) || !detail.ingredients.length) {
        bodyEl.innerHTML = '<tr><td colspan="4" class="muted">材料情報がありません。</td></tr>';
        return;
    }

    bodyEl.innerHTML = detail.ingredients
        .map((item) => {
            const missing = typeof item.missing_quantity_g === "number" ? item.missing_quantity_g : null;
            const statusChip = missing && missing > 0
                ? `<span class="status-chip warn">${missing.toFixed(1)}g不足</span>`
                : `<span class="status-chip ok">十分</span>`;
            const availableText = typeof item.available_quantity_g === "number"
                ? item.available_quantity_g.toFixed(1)
                : "-";
            return `
        <tr>
          <td>${item.food_name}</td>
          <td>${item.quantity_g.toFixed(1)}</td>
          <td>${availableText}</td>
          <td>${statusChip}</td>
        </tr>
      `;
        })
        .join("");
}

async function handleCookAction() {
    const servingsInput = document.getElementById("servingsInput");
    const cookBtn = document.getElementById("cookBtn");
    const servings = Number(servingsInput?.value || 1);
    if (!Number.isFinite(servings) || servings <= 0) {
        setStatusMessage("作る量には正の数を指定してください。", true);
        return;
    }

    let token;
    try {
        token = await ensureValidAccessToken();
    } catch (err) {
        console.debug("token refresh skipped", err);
    }
    if (!token) {
        setStatusMessage("在庫を消費するにはログインが必要です。", true);
        return;
    }

    if (cookBtn) {
        cookBtn.disabled = true;
        cookBtn.textContent = "在庫を更新中…";
    }
    setStatusMessage("在庫を更新しています…", false);

    try {
        const resp = await fetch(`${API_BASE_URL}/recipes/${currentRecipeId}/cook`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ servings }),
        });
        const body = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            throw new Error(body?.detail ?? `在庫更新に失敗しました (${resp.status})`);
        }
        const count = Array.isArray(body?.consumed) ? body.consumed.length : 0;
        setStatusMessage(`在庫を更新しました。${count}件の食材を消費しました。`, false);
        await loadRecipeDetail();
    } catch (err) {
        setStatusMessage(err?.message ?? "在庫の更新に失敗しました。", true);
    } finally {
        if (cookBtn) {
            cookBtn.disabled = false;
            cookBtn.textContent = "このレシピを作る";
        }
    }
}

function setStatusMessage(message, isError) {
    const messageEl = document.getElementById("cookMessage");
    if (!messageEl) return;
    if (!message) {
        messageEl.textContent = "";
        messageEl.className = "";
        return;
    }
    messageEl.textContent = message;
    messageEl.className = isError ? "warn" : "ok";
}

async function ensureValidAccessToken() {
    const accessKey = STORAGE_KEYS.accessToken;
    const refreshKey = STORAGE_KEYS.refreshToken;
    const expiresKey = STORAGE_KEYS.accessTokenExpiresAt;
    const expiresAt = Number(localStorage.getItem(expiresKey) || 0);
    const refreshToken = localStorage.getItem(refreshKey);
    const accessToken = localStorage.getItem(accessKey);

    if (accessToken && Date.now() < expiresAt - 5000) return accessToken;
    if (!refreshToken) throw new Error("no refresh token");
    return refreshAccessToken(refreshToken);
}

async function refreshAccessToken(refreshToken) {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
        localStorage.removeItem(STORAGE_KEYS.accessToken);
        localStorage.removeItem(STORAGE_KEYS.refreshToken);
        localStorage.removeItem(STORAGE_KEYS.accessTokenExpiresAt);
        throw new Error("token refresh failed");
    }
    const data = await response.json();
    const accessToken = data?.access_token;
    const expiresIn = Number(data?.expires_in ?? 0) * 1000;
    if (!accessToken || !expiresIn) throw new Error("invalid refresh response");
    localStorage.setItem(STORAGE_KEYS.accessToken, accessToken);
    localStorage.setItem(
        STORAGE_KEYS.accessTokenExpiresAt,
        String(Date.now() + expiresIn)
    );
    if (typeof data.refresh_token === "string" && data.refresh_token.length > 0) {
        localStorage.setItem(STORAGE_KEYS.refreshToken, data.refresh_token);
    }
    return accessToken;
}
