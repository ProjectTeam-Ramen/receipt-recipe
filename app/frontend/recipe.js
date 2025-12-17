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
  const preferencePanel = document.getElementById("preferencePanel");
  const preferenceList = document.getElementById("preferenceList");
  const preferenceSummary = document.getElementById("preferenceSummary");
  let backendRows = [];
  let backendPantryLabel = "";
  let backendPreferenceVector = [];
  let backendPreferenceLabels = [];
  let staticCatalog = [];

  const PREFERENCE_DIMENSIONS = [
    { key: "is_japanese", label: "和食", description: "和食ベース" },
    { key: "is_western", label: "洋食", description: "洋風テイスト" },
    { key: "is_chinese", label: "中華", description: "中華・アジアン" },
    { key: "is_main_dish", label: "主菜", description: "メイン料理" },
    { key: "is_side_dish", label: "副菜", description: "サイドメニュー" },
    { key: "is_soup", label: "汁物", description: "スープ・汁物" },
    { key: "is_dessert", label: "デザート", description: "甘いメニュー" },
    { key: "type_meat", label: "肉料理", description: "肉を使う" },
    { key: "type_seafood", label: "魚介", description: "魚・海鮮" },
    { key: "type_vegetarian", label: "菜食", description: "野菜中心" },
    { key: "type_composite", label: "複合", description: "肉＋魚など" },
    { key: "type_other", label: "その他", description: "分類外" },
    { key: "flavor_sweet", label: "甘め", description: "甘い味付け" },
    { key: "flavor_spicy", label: "辛め", description: "辛い味付け" },
    { key: "flavor_salty", label: "塩味", description: "塩気のある味" },
    { key: "texture_stewed", label: "煮込み", description: "煮る・ことこと" },
    { key: "texture_fried", label: "揚げ物", description: "揚げた食感" },
    { key: "texture_stir_fried", label: "炒め物", description: "炒める・ソテー" },
  ];

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

  // 初期表示用のダミーレシピは廃止（空配列）
  const DEFAULT_SAMPLE_RECIPES = [];

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
        const hasBackendDetail = r.fromBackend && (r.id !== undefined && r.id !== null);
        const detailHref = hasBackendDetail
          ? `recipe-detail.html?id=${encodeURIComponent(r.id)}`
          : r.url || `recipes/${r.id}.html`;
        const linkTarget = hasBackendDetail ? "_self" : "_blank";
        const relAttr = linkTarget === "_blank" ? ' rel="noopener"' : "";
        const coveragePercent =
          typeof r.coverage === "number" ? Math.round(r.coverage * 100) : null;
        const backendMeta =
          r.fromBackend && (coveragePercent !== null || Number.isFinite(r.score) || Number.isFinite(r.preference_score))
            ? `<p class="muted metric-line">${[
              coveragePercent !== null ? `カバー率: ${coveragePercent}%` : null,
              Number.isFinite(r.preference_score) ? `好み: ${r.preference_score.toFixed(2)}` : null,
              Number.isFinite(r.score) ? `総合: ${r.score.toFixed(2)}` : null,
            ]
              .filter(Boolean)
              .join(" / ")}</p>`
            : "";
        // 数値内訳（日本語ラベル）を付け加える
        let scoreDetails = "";
        if (r.fromBackend) {
          const cov = Number.isFinite(r.coverage) ? r.coverage : null;
          const pref = Number.isFinite(r.preference_score) ? r.preference_score : null;
          const final = Number.isFinite(r.score) ? r.score : null;
          let boost = null;
          if ((cov !== null || pref !== null) && final !== null) {
            const base = (cov !== null ? cov * 0.7 : 0) + (pref !== null ? pref * 0.3 : 0);
            if (base > 0) {
              boost = final / base - 1;
            }
          }
          const parts = [];
          if (cov !== null) parts.push(`カバー率: ${(cov * 100).toFixed(1)}`);
          if (pref !== null) parts.push(`好み: ${pref.toFixed(2)}`);
          if (boost !== null) {
            const sign = boost >= 0 ? "+" : "";
            parts.push(`ブースト: ${sign}${(boost * 100).toFixed(1)}`);
          }
          if (final !== null) parts.push(`最終: ${final.toFixed(3)}`);
          if (parts.length) {
            // Use inline element so it stays on the same line as other metadata
            scoreDetails = `<span class="muted score-details">${parts.join(' / ')}</span>`;
          }
        }
        const prepMeta =
          typeof r.prepTime === "number"
            ? `<p class="muted">調理時間: ${r.prepTime}分${typeof r.calories === "number" ? ` / 約${r.calories}kcal` : ""
            }</p>`
            : "";
        const detailBadge = hasBackendDetail
          ? '<p class="muted"><span class="badge">詳細ページあり</span></p>'
          : "";
        const boostBadge = r.isBoosted ? '<p class="muted"><span class="badge boost">賞味期限が近い食品を利用</span></p>' : '';
        const badgeBlock = r.canMake
          ? `<span class="badge ok">作れる</span>`
          : `<div class="badgeGroup">
                     <span class="badge">${r.haveCount ?? 0}/${r.needCount ?? 0
          } そろってる</span>
                     <span class="badge warn">不足: ${(r.missing || []).join("、")}</span>
                   </div>`;

        return `
      <article class="card" role="listitem">
        <a href="${detailHref}" class="card-link" target="${linkTarget}"${relAttr}>
          <div class="card-body">
            <h3 class="card-title">${r.title}</h3>
            ${badgeBlock}
            ${boostBadge}
              ${scoreDetails || backendMeta}
            ${prepMeta}
            ${detailBadge}
          </div>
        </a>
      </article>
    `;
      })
      .join("");
  }

  function updatePreferencePanel() {
    if (!preferencePanel || !preferenceSummary) return;
    const values = Array.isArray(backendPreferenceVector)
      ? backendPreferenceVector.map((val) => (Number.isFinite(Number(val)) ? Number(val) : 0))
      : [];
    const hasData = values.some((val) => Number.isFinite(val));
    if (!hasData) {
      preferencePanel.classList.add("is-empty");
      if (preferenceList) preferenceList.innerHTML = "";
      preferenceSummary.textContent = "提案を取得すると嗜好ベクトルの内訳が表示されます";
      return;
    }

    preferencePanel.classList.remove("is-empty");
    preferenceSummary.textContent = "値が大きいほど該当カテゴリを好む傾向 (0〜1目安)";

    if (!preferenceList) return;
    const labels = backendPreferenceLabels.length
      ? backendPreferenceLabels
      : PREFERENCE_DIMENSIONS.map((dim) => dim.key);
    const labelMeta = new Map(PREFERENCE_DIMENSIONS.map((dim) => [dim.key, dim]));
    const items = labels
      .map((key, idx) => {
        const value = Number(values[idx]);
        if (!Number.isFinite(value)) {
          return null;
        }
        const meta = labelMeta.get(key) || { label: key, description: "" };
        const description = meta.description ? `（${meta.description}）` : "";
        return `<li class="preference-item" role="listitem">
          <span>${meta.label}${description}</span>
          <strong>${value.toFixed(2)}</strong>
        </li>`;
      })
      .filter(Boolean);

    preferenceList.innerHTML = items.join("") || `<li class="preference-item" role="listitem">
        <span>嗜好ベクトル</span>
        <strong>${values.length && Number.isFinite(values[0]) ? values[0].toFixed(2) : "0.00"}</strong>
      </li>`;
  }

  function render() {
    let rows;
    if (backendRows.length) {
      rows = backendRows.slice();
      if (pantryInfo) {
        const label = backendPantryLabel && typeof backendPantryLabel !== "object"
          ? backendPantryLabel
          : (backendPantryLabel ? JSON.stringify(backendPantryLabel) : null) || `サーバー提案 ${rows.length}件`;
        pantryInfo.textContent = String(label);
      }
    } else {
      const pantry = getFridgeItems();
      if (pantryInfo) {
        pantryInfo.textContent = `手持ち: ${pantry.length} 点（localStorage参照。未設定なら仮データ）`;
      }
      const sourceCatalog = staticCatalog.length ? staticCatalog : DEFAULT_SAMPLE_RECIPES;
      rows = sourceCatalog.map((r) => scoreRecipe(r, pantry));
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
      backendPreferenceVector = Array.isArray(result.preferenceVector) ? result.preferenceVector : [];
      backendPreferenceLabels = Array.isArray(result.preferenceLabels) ? result.preferenceLabels : [];
      empty.textContent = "条件に合うレシピがありません";
      updatePreferencePanel();
      render();
    } catch (error) {
      backendRows = [];
      backendPantryLabel = "";
      backendPreferenceVector = [];
      backendPreferenceLabels = [];
      console.debug("backend recommendation skipped:", error);
      if (showAlertOnFail && window?.alert) {
        window.alert(error?.message || "レコメンド取得に失敗しました");
      }
      updatePreferencePanel();
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
  updatePreferencePanel();
  refreshRecommendationsFromBackend(false).catch((err) => {
    console.debug("initial backend recommendation skipped:", err);
  });

  loadStaticCatalogFromApi()
    .then((rows) => {
      staticCatalog = rows;
      render();
    })
    .catch((err) => {
      console.debug("static catalog load skipped:", err);
    });
});

async function loadStaticCatalogFromApi() {
  const resp = await fetch(`${API_BASE_URL}/recipes/static-catalog`);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail || `static catalog error ${resp.status}`);
  }
  const payload = await resp.json();
  if (!Array.isArray(payload)) return [];
  return payload
    .map((item, idx) => {
      const url = buildStaticRecipeUrl(item?.detail_path, item?.id ?? idx + 1);
      return {
        id: item?.id ?? `static-${idx}`,
        title: item?.title ?? `レシピ ${idx + 1}`,
        ingredients: Array.isArray(item?.ingredients) ? item.ingredients : [],
        url,
        prepTime: typeof item?.cooking_time === "number" ? item.cooking_time : null,
        calories: typeof item?.calories === "number" ? item.calories : null,
        fromStaticCatalog: true,
      };
    })
    .filter((row) => row.url && row.url !== "#");
}

function buildStaticRecipeUrl(detailPath, fallbackId) {
  let relativePath = null;
  if (typeof detailPath === "string" && detailPath.trim()) {
    const trimmed = detailPath.trim();
    relativePath = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  } else if (fallbackId !== undefined && fallbackId !== null) {
    const padded = padRecipeId(fallbackId);
    if (padded) {
      relativePath = `${STATIC_HTML_BASE_PATH}/${padded}.html`;
    }
  }
  if (!relativePath) return "#";
  if (/^https?:\/\//i.test(relativePath)) {
    return relativePath;
  }
  return `${BACKEND_BASE_URL}${relativePath}`;
}

function padRecipeId(value) {
  const num = Number(value);
  if (Number.isFinite(num)) {
    return String(num).padStart(4, "0");
  }
  const text = String(value ?? "").trim();
  return text ? text.padStart(4, "0") : null;
}

function deriveBackendBaseUrl() {
  try {
    const resolved = new URL(API_BASE_URL, window.location.origin);
    const origin = `${resolved.protocol}//${resolved.host}`;
    const trimmedPath = resolved.pathname.replace(/\/$/, "");
    const basePath = trimmedPath.endsWith("/api/v1")
      ? trimmedPath.slice(0, -"/api/v1".length)
      : trimmedPath;
    return basePath ? `${origin}${basePath}` : origin;
  } catch (err) {
    return window.location.origin.replace(/\/$/, "");
  }
}

// ---------------------- backend recommendation integration ----------------------
const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STATIC_HTML_BASE_PATH = "/recipe-pages";
const BACKEND_BASE_URL = deriveBackendBaseUrl();
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
};

async function loadBackendRecommendations(options = {}) {
  const maxTime = Number.isFinite(options.maxTime) ? options.maxTime : 60;
  const maxCalories = Number.isFinite(options.maxCalories) ? options.maxCalories : 2000;
  const allergies = Array.isArray(options.allergies) ? options.allergies : [];

  let resolvedUserId = null;
  let clientInventory = [];

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
        if (me?.id) resolvedUserId = me.id;
      }
    } catch (err) {
      console.debug("users/me fetch failed", err);
    }
  } else {
    const names = getFridgeItems();
    clientInventory = names.map((n) => ({
      name: n,
      quantity: "100",
      unit: "g",
      expiration_date: null,
    }));
    resolvedUserId = 1;
  }

  const payload = {
    max_time: maxTime,
    max_calories: maxCalories,
    allergies,
  };

  if (Number.isInteger(resolvedUserId)) {
    payload.user_id = resolvedUserId;
  }
  if (!authToken) {
    payload.inventory = clientInventory;
  }

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
      isBoosted: Boolean(p.is_boosted || p.isBoosted),
      score: typeof p.final_score === "number" ? p.final_score : Number(p.score || 0),
      coverage: typeof p.coverage_score === "number" ? p.coverage_score : haveCount / (needCount || 1),
      preference_score: typeof p.preference_score === "number" ? p.preference_score : 0,
      prepTime: p.prep_time ?? null,
      calories: p.calories ?? null,
      fromBackend: true,
    };
  });

  const responseMeta = proposals[0] || {};
  const responseInventoryCount = Number(responseMeta.inventory_count ?? 0);
  const fallbackCount = authToken ? responseInventoryCount : clientInventory.length;
  const fallbackLabel = authToken
    ? `所持食品数 ${fallbackCount}件`
    : `ローカル在庫 ${fallbackCount || clientInventory.length}件`;
  const inventoryLabelText = responseMeta.inventory_label || fallbackLabel;

  const preferenceSource = proposals.find((p) => Array.isArray(p.user_preference_vector));
  const preferenceVector = Array.isArray(preferenceSource?.user_preference_vector)
    ? preferenceSource.user_preference_vector.map((val) => (Number.isFinite(Number(val)) ? Number(val) : 0))
    : [];
  const preferenceLabels = Array.isArray(preferenceSource?.user_preference_labels)
    ? preferenceSource.user_preference_labels.map((label) => String(label))
    : [];

  const pantryLabel = `${inventoryLabelText} / 提案 ${rows.length}件`;
  return { rows, pantryLabel, preferenceVector, preferenceLabels };
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
