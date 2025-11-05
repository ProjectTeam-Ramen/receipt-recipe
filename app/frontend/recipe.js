document.addEventListener("DOMContentLoaded", () => {
  // 要素
  const backBtn = document.getElementById("backBtn");
  const grid = document.getElementById("suggestGrid");
  const empty = document.getElementById("empty");
  const canMakeOnly = document.getElementById("canMakeOnly");
  const maxMissing = document.getElementById("maxMissing");
  const maxMissingVal = document.getElementById("maxMissingVal");
  const sortByEl = document.getElementById("sortBy");
  const pantryInfo = document.getElementById("pantryInfo");

  if (backBtn) backBtn.addEventListener("click", () => (location.href = "home.html"));
  if (maxMissing) maxMissing.addEventListener("input", () => {
    maxMissingVal.textContent = maxMissing.value;
    render();
  });
  [canMakeOnly, sortByEl].forEach(el => el && el.addEventListener("change", render));

  // 手持ち食材（LocalStorageが無ければ仮の配列）
  function getFridgeItems() {
    try {
      const raw = localStorage.getItem("fridgeItems");
      const arr = raw ? JSON.parse(raw) : null;
      return Array.isArray(arr) ? arr : ["たまねぎ","にんじん","じゃがいも","しょうゆ","オリーブオイル"];
    } catch {
      return ["たまねぎ","にんじん","じゃがいも","しょうゆ","オリーブオイル"];
    }
  }

  // レシピ（ダミー）
  const catalog = [
    { id:"caprese", title:"トマトとモッツァレラのカプレーゼ", image:"https://picsum.photos/seed/caprese/600/400", url:"#",
      ingredients:["トマト","モッツァレラ","バジル","オリーブオイル","塩","こしょう"] },
    { id:"omelette", title:"ふわとろオムレツ", image:"https://picsum.photos/seed/omelette/600/400", url:"#",
      ingredients:["卵","バター","牛乳","塩","こしょう"] },
    { id:"miso", title:"具だくさん味噌汁", image:"https://picsum.photos/seed/miso/600/400", url:"#",
      ingredients:["味噌","だし","豆腐","わかめ","長ねぎ"] },
    { id:"yakitori", title:"ねぎま焼き鳥", image:"https://picsum.photos/seed/yakitori/600/400", url:"#",
      ingredients:["鶏もも肉","長ねぎ","塩"] },
    { id:"pasta", title:"ツナとトマトの簡単パスタ", image:"https://picsum.photos/seed/pasta/600/400", url:"#",
      ingredients:["スパゲッティ","ツナ缶","トマト","にんにく","オリーブオイル","塩"] },
    { id:"salad", title:"チキンシーザーサラダ", image:"https://picsum.photos/seed/salad/600/400", url:"#",
      ingredients:["鶏むね肉","レタス","クルトン","粉チーズ","マヨネーズ"] }
  ];

  // 表記ゆれ（最低限）
  const aliasMap = { "ねぎ":"長ねぎ", "ネギ":"長ねぎ", "オリーブ油":"オリーブオイル", "胡椒":"こしょう", "醤油":"しょうゆ" };
  const norm = s => (aliasMap[s] || s).trim().toLowerCase();

  // 常備品（不足判定から外す）
  const STAPLES = new Set(["塩","こしょう","砂糖","しょうゆ","みりん","酒","水","油","オリーブオイル","だし"]);

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
        <a href="${r.url}" class="card-link">
          <figure class="card-figure"><img src="${r.image}" alt="${r.title}" loading="lazy"></figure>
          <div class="card-body">
            <h3 class="card-title">${r.title}</h3>
            ${
              r.canMake
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
      if (key === "score")    return b.score - a.score;
      if (key === "coverage") return b.coverage - a.coverage;
      if (key === "missing")  return a.missing.length - b.missing.length;
      if (key === "title")    return a.title.localeCompare(b.title, "ja");
      return 0;
    });

    renderCards(rows);
  }

  // 初回
  render();
});
