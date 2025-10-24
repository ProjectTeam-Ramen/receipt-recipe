// ==============================
// 冷蔵庫：食材一覧ページ用スクリプト
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const checkList = document.getElementById("checkList");

  // 冷蔵庫ホームに戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-home.html";
  });

  // 仮データ（今後localStorage連携可能）
  let ingredients = ["卵", "牛乳", "トマト", "レタス"];

  // 食材一覧を描画
  function renderList() {
    if (ingredients.length === 0) {
      checkList.innerHTML = `<p>現在、冷蔵庫に登録されている食材はありません。</p>`;
      return;
    }

    checkList.innerHTML = ingredients
      .map(
        (item) => `
        <div class="check-item">
          <span>${item}</span>
        </div>`
      )
      .join("");
  }

  renderList();
});
