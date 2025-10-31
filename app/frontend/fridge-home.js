<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>レシピ検索</title>
  <link rel="stylesheet" href="style.css"/>
  <style>
    /* 雛形でも見やすいように軽く整える（既存style.cssがあれば最小でOK） */
    header { display:flex; justify-content:space-between; align-items:center; padding:12px 16px; border-bottom:1px solid #eee; }
    main { max-width:960px; margin:0 auto; padding:16px; }
    .controls { display:grid; gap:12px; grid-template-columns: 1fr; margin-bottom:16px; }
    .controls > div { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .recipes { display:grid; gap:12px; }
    .card { border:1px solid #e5e5e5; border-radius:12px; padding:12px 14px; }
    .badges { display:flex; gap:8px; flex-wrap:wrap; margin:6px 0; }
    .badge { font-size:12px; border-radius:999px; padding:4px 8px; background:#f3f4f6; }
    .ok    { background:#def7ec; }
    .warn  { background:#fde68a; }
    .danger{ background:#fecaca; }
    .muted { color:#6b7280; }
    .list { margin:6px 0 0 0; padding-left:18px; }
    .row { display:flex; gap:10px; align-items:center; }
    .grow { flex:1; }
    .right { margin-left:auto; }
    .empty { text-align:center; color:#808080; padding:24px; border:1px dashed #ddd; border-radius:12px; }
    .small { font-size:12px; }
    input[type="range"] { width:180px; }
    .pill { padding:2px 8px; border-radius:999px; background:#eef2ff; font-size:12px; }
  </style>
</head>
<body>
  <header>
    <h1>レシピ検索</h1>
    <button id="backBtn" class="logout-btn">ホームに戻る</button>
  </header>

  <main>
    <section class="controls">
      <div class="row">
        <input id="q" class="grow" type="search" placeholder="レシピ名・食材で検索（例: カレー / じゃがいも）">
        <label class="row small">
          <input id="canMakeOnly" type="checkbox"> 作れるだけ
        </label>
        <label class="row small">
          不足最大数
          <input id="maxMissing" type="range" min="0" max="5" value="2">
          <span id="maxMissingVal" class="pill">2</span>
        </label>
        <label class="row small">
          並べ替え
          <select id="sortBy">
            <option value="score">スコア高い順</option>
            <option value="coverage">カバー率高い順</option>
            <option value="missing">不足少ない順</option>
            <option value="title">タイトル順</option>
          </select>
        </label>
      </div>
      <div class="row small">
        除外したい食材（カンマ区切り）:
        <input id="exclude" class="grow" type="text" placeholder="例: ねぎ, 卵">
      </div>
    </section>

    <section class="small muted" id="pantryInfo"></section>

    <section class="recipes" id="list"></section>
    <div class="empty" id="empty" style="display:none;">条件に合うレシピがありません</div>
  </main>

  <script src="recipe.js"></script>
</body>
</html>

