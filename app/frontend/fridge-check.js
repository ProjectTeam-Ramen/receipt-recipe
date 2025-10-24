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

  // 仮データ（name: 食材名, amount: g単位）
  let ingredients = [
    { name: "卵", amount: 300 },
    { name: "牛乳", amount: 1000 },
    { name: "トマト", amount: 500 },
    { name: "レタス", amount: 250 }
  ];

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
          <span class="item-name">${item.name}</span>
          <span class="item-amount">${item.amount}g</span>
        </div>`
      )
      .join("");
  }

  renderList();
});

