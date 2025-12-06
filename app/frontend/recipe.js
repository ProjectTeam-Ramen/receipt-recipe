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

  if (backBtn) backBtn.addEventListener("click", () => (location.href = "home.html"));
  if (maxMissing) maxMissing.addEventListener("input", () => {
    maxMissingVal.textContent = maxMissing.value;
    render();
  });
  [canMakeOnly, sortByEl].forEach(el => el && el.addEventListener("change", render));
  if (applyRecommendBtn) applyRecommendBtn.addEventListener("click", () => {
    loadBackendRecommendations().catch((err) => console.debug('apply recommend failed', err));
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
    if (!grid) return;
    if (!list.length) {
      empty.style.display = "";
      grid.innerHTML = "";
      return;
    }
    empty.style.display = "none";
    grid.innerHTML = list.map(r => `
      <article class="card" role="listitem">
        <a href="recipes/${r.id}.html" class="card-link">
          <figure class="card-figure"><img src="${r.image}" alt="${r.title}" loading="lazy"></figure>
          <div class="card-body">
            <h3 class="card-title">${r.title}</h3>
            ${r.canMake
        ? `<span class="badge ok">作れる</span>`
        : `<div class="badgeGroup">
                     <span class="badge">${r.haveCount}/${r.needCount} そろってる</span>
                     <span class="badge warn">不足: ${r.missing.join("、")}</span>
                   </div>`
      }
          </div>
        </a>
      </article>
    `).join("");
  }

  function render() {
    const pantry = getFridgeItems();
    pantryInfo.textContent = `手持ち: ${pantry.length} 点（localStorage参照。未設定なら仮データ）`;

    // 採点 → 絞り込み → ソート
    let rows = catalog.map(r => scoreRecipe(r, pantry));

    // 作れるだけ
    if (canMakeOnly.checked) rows = rows.filter(r => r.canMake);

    // 不足最大数
    const maxM = Number(maxMissing.value);
    rows = rows.filter(r => r.missing.length <= maxM);

    // ソート
    const key = sortByEl.value;
    rows.sort((a, b) => {
      if (key === "score") return b.score - a.score;
      if (key === "coverage") return b.coverage - a.coverage;
      if (key === "missing") return a.missing.length - b.missing.length;
      if (key === "title") return a.title.localeCompare(b.title, "ja");
      return 0;
    });

    renderCards(rows);
  }

  // 初回
  render();
  // すぐにバックエンド版の提案を取得して差し替えを試みる
  loadBackendRecommendations().catch((err) => {
    // 失敗してもローカルカタログ表示は残す
    console.debug("backend recommendation skipped:", err);
  });
});

// ---------------------- backend recommendation integration ----------------------
const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
};

async function loadBackendRecommendations() {
  // Try to obtain inventory from authenticated API; fallback to localStorage names
  let inventory = [];
  const refreshToken = localStorage.getItem(STORAGE_KEYS.refreshToken);
  let userId = 1; // default fallback

  if (refreshToken) {
    const token = await ensureValidAccessToken();
    // try to get user id
    try {
      const me = await fetch(`${API_BASE_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => r.json());
      if (me && me.id) userId = me.id;
    } catch (e) {
      console.debug("users/me fetch failed", e);
    }

    // get ingredients from API
    try {
      const ingResp = await fetch(`${API_BASE_URL}/ingredients`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (ingResp.ok) {
        const data = await ingResp.json();
        const items = data?.ingredients ?? [];
        inventory = items.map((it) => ({
          name: it.food_name,
          quantity: Number(it.quantity_g) || 0,
          unit: "g",
          expiration_date: it.expiration_date || null,
        }));
      }
    } catch (e) {
      console.debug("ingredient fetch failed", e);
    }
  }

  if (!inventory.length) {
    // fallback to localStorage simple names (assign heuristic qty 100g)
    const raw = localStorage.getItem("fridgeItems");
    const arr = raw ? JSON.parse(raw) : null;
    const names = Array.isArray(arr) ? arr : ["たまねぎ", "にんじん", "じゃがいも"];
    inventory = names.map((n) => ({ name: n, quantity: 100.0, unit: "g", expiration_date: null }));
  }

  const payload = {
    user_id: userId,
    max_time: (() => {
      try { return Number(document.getElementById('maxTime')?.value) || 60 } catch { return 60 }
    })(),
    max_calories: (() => {
      try { return Number(document.getElementById('maxCalories')?.value) || 2000 } catch { return 2000 }
    })(),
    allergies: (() => {
      try { const v = (document.getElementById('allergies')?.value || '').split(',').map(s => s.trim()).filter(Boolean); return v } catch { return [] }
    })(),
    inventory: inventory,
  };

  const tokenForReq = await (localStorage.getItem(STORAGE_KEYS.accessToken) || Promise.resolve(null));
  const headers = { "Content-Type": "application/json" };
  if (tokenForReq) headers.Authorization = `Bearer ${tokenForReq}`;

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
  if (!Array.isArray(proposals) || proposals.length === 0) {
    throw new Error("no proposals");
  }

  // convert proposals to card-friendly items and render
  const rows = proposals.map((p) => ({
    id: p.recipe_id || p.recipe_id || Math.random().toString(36).slice(2, 9),
    title: p.recipe_name || p.name || "レシピ",
    image: p.image || `https://picsum.photos/seed/${encodeURIComponent(p.recipe_name || "r")}/600/400`,
    ingredients: p.required_items || p.required_qty ? Object.keys(p.required_qty || {}) : [],
    missing: p.missing_items || [],
    haveCount: (p.req_count || 0) - (p.missing_items || []).length,
    needCount: p.req_count || (p.required_qty ? Object.keys(p.required_qty).length : 0),
    canMake: (p.missing_items || []).length === 0,
    score: p.final_score || p.score || 0,
  }));

  renderCards(rows);
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
