// ==============================
// レシピ検索ページ用スクリプト
// ==============================

// ホーム画面に戻るボタン
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const recipeForm = document.getElementById("recipeForm");
  const ingredientInput = document.getElementById("ingredientInput");
  const resultArea = document.getElementById("resultArea");

  // ホームに戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "home.html";
  });

  // 検索ボタン押下時の処理
  recipeForm.addEventListener("submit", (event) => {
    event.preventDefault(); // ページのリロードを防ぐ
    const ingredient = ingredientInput.value.trim();

    // 入力チェック
    if (ingredient === "") {
      resultArea.innerHTML = `<p style="color:red;">食材を入力してください。</p>`;
      return;
    }

    // 一時的なロード表示
    resultArea.innerHTML = `<p>「${ingredient}」を使ったレシピを検索中...</p>`;

    // --- 仮のデータ（将来的にAPI連携可） ---
    setTimeout(() => {
      // サンプル結果の表示（固定例）
      resultArea.innerHTML = `
        <div class="recipe-card">
          <img src="https://via.placeholder.com/200x150" alt="レシピ画像">
          <h3>${ingredient}のオムレツ</h3>
          <p>シンプルで美味しい家庭の味。</p>
        </div>
        <div class="recipe-card">
          <img src="https://via.placeholder.com/200x150" alt="レシピ画像">
          <h3>${ingredient}とチーズのパスタ</h3>
          <p>簡単・時短・満足の一品。</p>
        </div>
      `;
    }, 800);
  });
});
