// ==============================
// レシピ検索：雛形（データ未完成でも動く）
// ==============================

document.addEventListener("DOMContentLoaded", () => {
  // ====== 1) 画面要素 ======
  const backBtn     = document.getElementById("backBtn");
  const listEl      = document.getElementById("list");
  const emptyEl     = document.getElementById("empty");
  const qEl         = document.getElementById("q");
  const canMakeOnly = document.getElementById("canMakeOnly");
  const maxMissing  = document.getElementById("maxMissing");
  const maxMissingVal = document.getElementById("maxMissingVal");
  const sortByEl    = document.getElementById("sortBy");
  const excludeEl   = document.getElementById("exclude");
  const pantryInfo  = document.getElementById("pantryInfo");

  backBtn.addEventListener("click", () => {
    window.location.href = "home.html";
  });

  maxMissing.addEventListener("input", () => {
    maxMissingVal.textContent = maxMissing.value;
    render();
  });

  [qEl, canMakeOnly, sortByEl, excludeEl].forEach(el => {
    el.addEventListener("input", render);
    el.addEventListener("change", render);
  });

  // ====== 2) モックデータ（あとで差し替え） ======
  // 冷蔵庫データは localStorage("fridgeItems") を優先。無ければ仮データ。
  const pantry = readPantry();
  // レシピは仮配列。あとでデータセットに置き換えOK。
  const RECIPES = [
    {
      id: "r1",
      title: "シンプル野菜スープ",
      ingredients: ["たまねぎ", "にんじん", "じゃがいも", "塩", "こしょう", "水"],
      optionals: ["コンソメ", "ベーコン"]
    },
    {
      id: "r2",
      title: "親子丼",
      ingredients: ["鶏もも肉", "たまご", "たまねぎ", "だし", "しょうゆ", "みりん", "砂糖", "ごはん"],
      optionals: ["三つ葉"]
    },
    {
      id: "r3",
      title: "和風パスタ",
      ingredients: ["パスタ", "しめじ", "ベーコン", "にんにく", "オリーブオイル", "しょうゆ"],
      optionals: ["刻みのり", "バター"]
    },
    {
      id: "r4",
      title: "カレー（簡易）",
      ingredients: ["カレールウ", "たまねぎ", "にんじん", "じゃがいも", "水"],
      optionals: ["豚こま", "にんにく"]
    },
  ];

  // 常備品：不足計算からは外す（※好みに応じて調整してね）
  const STAPLES = new Set(["塩", "こしょう", "砂糖", "しょうゆ", "みりん", "酒", "水", "油", "オリーブオイル", "だし"]);

  // 表記ゆれ対策（最低限）
  const SYNONYMS = {
    "玉ねぎ": "たまねぎ",
    "長ネギ": "長ねぎ",
    "ねぎ": "長ねぎ",
    "ニンジン": "にんじん",
    "ジャガイモ": "じゃがいも",
    "卵": "たまご",
    "にく": "肉",
    // 必要になったら増やす
  };

  const normalize = (s) =>
    s.trim().toLowerCase()
      .replace(/\s+/g, " ")
      .replace(/（.*?）|\(.*?\)/g, "");

  const normName = (s) => SYNONYMS[normalize(s)] ?? normalize(s);

  function readPantry() {
    // localStorageに "fridgeItems" があればそれを使う（["たまねぎ","にんじん",...] の配列想定）
    try {
      const raw = localStorage.getItem("fridgeItems");
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) return arr;
      }
    } catch (_) {}
    // 無ければ仮の手持ち（あとで自由に差し替え）
    return ["たまねぎ", "にんじん", "じゃがいも", "ベーコン", "しょうゆ", "ごはん", "オリーブオイル"];
  }

  // ====== 3) スコア計算 ======
  function scoreRecipe(recipe, pantryArr) {
    const have = new Set(pantryArr.map(normName));
    const req  = recipe.ingredients.map(normName);
    const opt  = (recipe.optionals ?? []).map(normName);

    const missing = req.filter(x => !have.has(x) && !STAPLES.has(x));
    const covered = req.length - missing.length;
    const coverage = req.length === 0 ? 1 : covered / req.length;

    // オプションを持っていたら少し加点、足りない数は少し減点（雛形なので単純に）
    const optHit = opt.filter(x => have.has(x)).length;
    const score  = coverage + 0.05 * optHit - 0.01 * missing.length;

    return {
      score,
      coverage,
      missing,
      haveOptional: optHit,
      canMake: missing.length === 0
    };
  }

  // ====== 4) フィルタ＆ソート ======
  function applyFilter(recipes) {
    const q = normalize(qEl.value || "");
    const excludes = (excludeEl.value || "")
      .split(",")
      .map(s => s.trim())
      .filter(Boolean)
      .map(normName);

    const pantryNorm = pantry.map(normName);

    // まずスコアを付ける
    let rows = recipes.map(r => {
      const s = scoreRecipe(r, pantryNorm);
      return { recipe: r, ...s };
    });

    // キーワード（タイトル or 食材）マッチ
    if (q) {
      rows = rows.filter(({ recipe }) => {
        const t = normalize(recipe.title);
        const ing = recipe.ingredients.map(normalize).join(" ");
        return t.includes(q) || ing.includes(q);
      });
    }

    // 除外食材が含まれているレシピは落とす
    if (excludes.length) {
      rows = rows.filter(({ recipe }) => {
        const all = recipe.ingredients.concat(recipe.optionals ?? []).map(normName);
        return !excludes.some(ex => all.includes(ex));
      });
    }

    // 「作れるだけ」
    if (canMakeOnly.checked) {
      rows = rows.filter(r => r.canMake);
    }

    // 「不足最大数」
    const maxM = Number(maxMissing.value);
    rows = rows.filter(r => r.missing.length <= maxM);

    // 並べ替え
    const key = sortByEl.value;
    rows.sort((a, b) => {
      if (key === "score")    return b.score - a.score;
      if (key === "coverage") return b.coverage - a.coverage;
      if (key === "missing")  return a.missing.length - b.missing.length;
      if (key === "title")    return a.recipe.title.localeCompare(b.recipe.title, "ja");
      return 0;
    });

    return rows;
  }

  // ====== 5) 表示 ======
  function render() {
    // パントリー情報
    pantryInfo.innerHTML = `現在の手持ち食材（推定）: <span class="pill">${pantry.length} 点</span>　<span class="small">（localStorageの "fridgeItems" を参照。無ければ仮データ）</span>`;

    const rows = applyFilter(RECIPES);

    listEl.innerHTML = "";
    if (!rows.length) {
      emptyEl.style.display = "";
      return;
    }
    emptyEl.style.display = "none";

    for (const row of rows) {
      const { recipe, score, coverage, missing, haveOptional, canMake } = row;

      const badge =
        canMake ? `<span class="badge ok">作れる</span>` :
        missing.length === 1 ? `<span class="badge warn">あと1個</span>` :
        `<span class="badge danger">不足 ${missing.length} 個</span>`;

      const optBadge = haveOptional > 0 ? `<span class="badge">オプション ${haveOptional} あり</span>` : "";

      const missingList = missing.length
        ? `<div class="small muted">不足: <ul class="list">${missing.map(x => `<li>${x}</li>`).join("")}</ul></div>`
        : "";

      const el = document.createElement("article");
      el.className = "card";
      el.innerHTML = `
        <div class="row">
          <h3 class="grow">${recipe.title}</h3>
          <div class="badges">
            ${badge}
            ${optBadge}
            <span class="badge">カバー率 ${(coverage*100).toFixed(0)}%</span>
            <span class="badge">スコア ${score.toFixed(2)}</span>
          </div>
        </div>
        <div class="small muted">材料: ${recipe.ingredients.join(" / ")}</div>
        ${missingList}
      `;
      listEl.appendChild(el);
    }
  }

  // 初回表示
  render();
});
