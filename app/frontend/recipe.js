document.addEventListener("DOMContentLoaded", () => {
  // 要素
  const backBtn = document.getElementById("backBtn");
  const grid = document.getElementById("suggestGrid");
  const empty = document.getElementById("empty");
  const canMakeOnly = document.getElementById("canMakeOnly");
  const maxTimeEl = document.getElementById("maxTime");
  const maxCaloriesEl = document.getElementById("maxCalories");
  const allergiesEl = document.getElementById("allergies");
  const maxMissing = document.getElementById("maxMissing");
  const maxMissingVal = document.getElementById("maxMissingVal");
  const sortByEl = document.getElementById("sortBy");
  const pantryInfo = document.getElementById("pantryInfo");
  const applyRecommendBtn = document.getElementById("applyRecommendBtn");
  let backendRows = [];
  let backendPantryLabel = "";

  if (backBtn) backBtn.addEventListener("click", () => (location.href = "home.html"));
  if (maxMissing) {
    if (maxMissingVal) maxMissingVal.textContent = maxMissing.value;
    maxMissing.addEventListener("input", () => {
      if (maxMissingVal) maxMissingVal.textContent = maxMissing.value;
      render();
    });
  }
  [canMakeOnly, sortByEl].forEach(el => el && el.addEventListener("change", render));
  if (applyRecommendBtn) applyRecommendBtn.addEventListener("click", () => {
    refreshRecommendationsFromBackend(true).catch((err) => console.debug('apply recommend failed', err));
  });

  // 手持ち食材（LocalStorageが無ければ仮の配列）
  function getFridgeItems() {
    try {
      const raw = localStorage.getItem("fridgeItems");
      const arr = raw ? JSON.parse(raw) : null;
      return Array.isArray(arr) ? arr : ["たまねぎ", "にんじん", "じゃがいも", "しょうゆ", "オリーブオイル"];
    } catch {
      return ["たまねぎ", "にんじん", "じゃがいも", "しょうゆ", "オリーブオイル"];
    }
  }

  // レシピ（ダミー）
  const catalog = [
    {
      id: "caprese", title: "トマトとモッツァレラのカプレーゼ", image: "https://picsum.photos/seed/caprese/600/400", url: "#",
      ingredients: ["トマト", "モッツァレラ", "バジル", "オリーブオイル", "塩", "こしょう"]
    },
    {
      id: "omelette", title: "ふわとろオムレツ", image: "https://picsum.photos/seed/omelette/600/400", url: "#",
      ingredients: ["卵", "バター", "牛乳", "塩", "こしょう"]
    },
    {
      id: "miso", title: "具だくさん味噌汁", image: "https://picsum.photos/seed/miso/600/400", url: "#",
      ingredients: ["味噌", "だし", "豆腐", "わかめ", "長ねぎ"]
    },
    {
      id: "yakitori", title: "ねぎま焼き鳥", image: "https://picsum.photos/seed/yakitori/600/400", url: "#",
      ingredients: ["鶏もも肉", "長ねぎ", "塩"]
    },
    {
      id: "pasta", title: "ツナとトマトの簡単パスタ", image: "https://picsum.photos/seed/pasta/600/400", url: "#",
      ingredients: ["スパゲッティ", "ツナ缶", "トマト", "にんにく", "オリーブオイル", "塩"]
    },
    {
      id: "salad", title: "チキンシーザーサラダ", image: "https://picsum.photos/seed/salad/600/400", url: "#",
      ingredients: ["鶏むね肉", "レタス", "クルトン", "粉チーズ", "マヨネーズ"]
    }
  ];

  // 表記ゆれ（最低限）
  const aliasMap = { "ねぎ": "長ねぎ", "ネギ": "長ねぎ", "オリーブ油": "オリーブオイル", "胡椒": "こしょう", "醤油": "しょうゆ" };
  const norm = s => (aliasMap[s] || s).trim().toLowerCase();

  // 常備品（不足判定から外す）
  const STAPLES = new Set(["塩", "こしょう", "砂糖", "しょうゆ", "みりん", "酒", "水", "油", "オリーブオイル", "だし"]);

  // 採点
  function scoreRecipe(recipe, fridge) {
    const haveSet = new Set(fridge.map(norm));
    const need = recipe.ingredients.map(norm);
    const missing = need.filter(x => !haveSet.has(x) && !STAPLES.has(x));
    const haveCount = need.length - missing.length;
    const coverage = need.length ? haveCount / need.length : 1;
    const score = coverage - 0.01 * missing.length; // シンプル指標

    return {
      ...recipe,
      missing,
      haveCount,
      needCount: need.length,
      coverage,
      score,
      canMake: missing.length === 0
    };
  }

  function renderCards(list) {
    if (!grid || !empty) return;
    if (!list.length) {
      empty.style.display = "";
      grid.innerHTML = "";
      return;
    }
    empty.style.display = "none";
    grid.innerHTML = list
      .map((r) => {
        const href = r.url || `recipes/${r.id}.html`;
        const coveragePercent =
          typeof r.coverage === "number" ? Math.round(r.coverage * 100) : null;
        const backendMeta =
          r.fromBackend && (coveragePercent !== null || Number.isFinite(r.score))
            ? `<p class="muted">カバー率: ${coveragePercent !== null ? `${coveragePercent}%` : "-"
            } / スコア: ${Number.isFinite(r.score) ? r.score.toFixed(2) : "-"}</p>`
            : "";
        const prepMeta =
          typeof r.prepTime === "number"
            ? `<p class="muted">調理時間: ${r.prepTime}分${typeof r.calories === "number" ? ` / 約${r.calories}kcal` : ""
            }</p>`
            : "";
        const badgeBlock = r.canMake
          ? `<span class="badge ok">作れる</span>`
          : `<div class="badgeGroup">
                     <span class="badge">${r.haveCount ?? 0}/${r.needCount ?? 0
          } そろってる</span>
                     <span class="badge warn">不足: ${(r.missing || []).join("、")}</span>
                   </div>`;

        return `
      <article class="card" role="listitem">
        <a href="${href}" class="card-link" target="_blank" rel="noopener">
          <div class="card-body">
            <h3 class="card-title">${r.title}</h3>
            ${badgeBlock}
            ${backendMeta}
            ${prepMeta}
          </div>
        </a>
      </article>
    `;
      })
      .join("");
  }

  function render() {
    let rows;
    if (backendRows.length) {
      rows = backendRows.slice();
      if (pantryInfo) {
        pantryInfo.textContent = backendPantryLabel || `サーバー提案 ${rows.length}件`;
      }
    } else {
      const pantry = getFridgeItems();
      if (pantryInfo) {
        pantryInfo.textContent = `手持ち: ${pantry.length} 点（localStorage参照。未設定なら仮データ）`;
      }
      rows = catalog.map((r) => scoreRecipe(r, pantry));
    }

    const maxM = maxMissing ? Number(maxMissing.value) : 5;
    rows = rows.filter((r) => (r.missing ? r.missing.length : 0) <= maxM);
    if (canMakeOnly?.checked) rows = rows.filter((r) => r.canMake);

    const key = sortByEl?.value || "score";
    rows.sort((a, b) => {
      if (key === "score") return (b.score || 0) - (a.score || 0);
      if (key === "coverage") return (b.coverage || 0) - (a.coverage || 0);
      if (key === "missing") return (a.missing?.length || 0) - (b.missing?.length || 0);
      if (key === "title") return (a.title || "").localeCompare(b.title || "", "ja");
      return 0;
    });

    renderCards(rows);
  }

  async function refreshRecommendationsFromBackend(showAlertOnFail = false) {
    const btn = applyRecommendBtn;
    const previousLabel = btn?.textContent;
    if (btn) {
      btn.disabled = true;
      btn.textContent = "提案取得中…";
    }
    try {
      const result = await loadBackendRecommendations({
        maxTime: Number(maxTimeEl?.value) || 60,
        maxCalories: Number(maxCaloriesEl?.value) || 2000,
        allergies: (allergiesEl?.value || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      backendRows = result.rows;
      backendPantryLabel = result.pantryLabel;
      empty.textContent = "条件に合うレシピがありません";
      render();
    } catch (error) {
      backendRows = [];
      backendPantryLabel = "";
      console.debug("backend recommendation skipped:", error);
      if (showAlertOnFail && window?.alert) {
        window.alert(error?.message || "レコメンド取得に失敗しました");
      }
      render();
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = previousLabel ?? "提案を取得";
      }
    }
  }

  // 初回
  render();
  refreshRecommendationsFromBackend(false).catch((err) => {
    console.debug("initial backend recommendation skipped:", err);
  });
});

// ---------------------- backend recommendation integration ----------------------
const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
};

async function loadBackendRecommendations(options = {}) {
  const maxTime = Number.isFinite(options.maxTime) ? options.maxTime : 60;
  const maxCalories = Number.isFinite(options.maxCalories) ? options.maxCalories : 2000;
  const allergies = Array.isArray(options.allergies) ? options.allergies : [];

  let inventory = [];
  let inventorySource = "local";
  let userId = 1;

  const refreshToken = localStorage.getItem(STORAGE_KEYS.refreshToken);
  let authToken = null;
  if (refreshToken) {
    try {
      authToken = await ensureValidAccessToken();
    } catch (err) {
      console.debug("token refresh skipped", err);
    }
  }

  if (authToken) {
    try {
      const meResp = await fetch(`${API_BASE_URL}/users/me`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (meResp.ok) {
        const me = await meResp.json();
        if (me?.id) userId = me.id;
      }
    } catch (err) {
      console.debug("users/me fetch failed", err);
    }

    try {
      const ingResp = await fetch(`${API_BASE_URL}/ingredients`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (ingResp.ok) {
        const data = await ingResp.json();
        const items = Array.isArray(data?.ingredients) ? data.ingredients : [];
        inventory = items
          .map((it) => ({
            name: String(it.food_name ?? it.name ?? "").trim(),
            quantity: String(Number(it.quantity_g ?? it.quantity ?? 0) || 0),
            unit: "g",
            expiration_date: it.expiration_date || null,
          }))
          .filter((row) => row.name);
        if (inventory.length) {
          inventorySource = "api";
        }
      }
    } catch (err) {
      console.debug("ingredient fetch failed", err);
    }
  }

  if (!inventory.length) {
    let names = [];
    try {
      const raw = localStorage.getItem("fridgeItems");
      const arr = raw ? JSON.parse(raw) : null;
      names = Array.isArray(arr) ? arr : [];
    } catch (err) {
      console.debug("local fridge parse failed", err);
    }
    if (!names.length) names = ["たまねぎ", "にんじん", "じゃがいも"];
    inventory = names.map((n) => ({
      name: n,
      quantity: "100",
      unit: "g",
      expiration_date: null,
    }));
    inventorySource = "local";
  }

  const payload = {
    user_id: userId,
    max_time: maxTime,
    max_calories: maxCalories,
    allergies,
    inventory,
  };

  const headers = { "Content-Type": "application/json" };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const resp = await fetch(`${API_BASE_URL}/recommendation/propose`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail || `recommendation error ${resp.status}`);
  }

  const proposals = await resp.json();
  if (!Array.isArray(proposals) || !proposals.length) {
    throw new Error("no proposals");
  }

  const rows = proposals.map((p, idx) => {
    const required = p.required_qty || {};
    const missingItems = Array.isArray(p.missing_items) ? p.missing_items : [];
    const normalizedMissing = missingItems
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const name = item.name ?? item.food_name ?? item.ingredient ?? "";
          const detail = item.detail ?? item.message ?? "";
          const shortage =
            item.shortage ?? item.missing ?? item.required ?? item.quantity ?? item.amount;
          if (detail && !name) return String(detail);
          if (name && shortage !== undefined) return `${name} (${shortage})`;
          if (name) return String(name);
          try {
            return JSON.stringify(item);
          } catch (err) {
            return String(item);
          }
        }
        return String(item ?? "").trim();
      })
      .filter((text) => typeof text === "string" && text.trim().length > 0);

    const needCount = p.req_count || Object.keys(required).length || 0;
    const haveCount = Math.max(0, needCount - normalizedMissing.length);
    return {
      id: p.recipe_id ?? `recipe-${idx}`,
      title: p.recipe_name ?? p.name ?? `レシピ ${idx + 1}`,
      image:
        p.image_url ||
        p.image ||
        `https://picsum.photos/seed/${encodeURIComponent(p.recipe_name ?? `recipe-${idx}`)}/600/400`,
      url: "#",
      ingredients: Object.keys(required),
      missing: normalizedMissing,
      haveCount,
      needCount,
      canMake: normalizedMissing.length === 0,
      score: typeof p.final_score === "number" ? p.final_score : Number(p.score || 0),
      coverage: typeof p.coverage_score === "number" ? p.coverage_score : haveCount / (needCount || 1),
      preference_score: typeof p.preference_score === "number" ? p.preference_score : 0,
      prepTime: p.prep_time ?? null,
      calories: p.calories ?? null,
      fromBackend: true,
    };
  });

  const pantryLabel = `${inventorySource === "api" ? "サーバー在庫" : "ローカル在庫"} ${inventory.length}件 / 提案 ${rows.length}件`;
  return { rows, pantryLabel };
}

// Token refresh utilities (copied minimal from other frontend files)
async function ensureValidAccessToken() {
  const accessKey = STORAGE_KEYS.accessToken;
  const refreshKey = STORAGE_KEYS.refreshToken;
  const expiresKey = STORAGE_KEYS.accessTokenExpiresAt;
  const expiresAt = Number(localStorage.getItem(expiresKey) || 0);
  const refreshToken = localStorage.getItem(refreshKey);
  let accessToken = localStorage.getItem(accessKey);

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
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) {
    throw new Error(data?.detail || "failed refresh");
  }
  const accessKey = STORAGE_KEYS.accessToken;
  const expiresKey = STORAGE_KEYS.accessTokenExpiresAt;
  const expiresIn = Number(data.expires_in ?? 1800) * 1000;
  localStorage.setItem(accessKey, data.access_token);
  localStorage.setItem(expiresKey, String(Date.now() + expiresIn));
  return data.access_token;
}
