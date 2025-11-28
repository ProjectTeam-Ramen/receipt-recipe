// ==============================
// 食材追加ページ (food-add.js)
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const foodForm = document.getElementById("foodForm");
  const messageArea = document.getElementById("messageArea");

  // 戻るボタンで管理ページに戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-control.html";
  });

  // 食材追加フォーム送信
  foodForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const name = document.getElementById("foodName").value.trim();
    const amount = document.getElementById("foodAmount").value.trim();

    if (!name || !amount) {
      messageArea.innerHTML = `<p class="error">すべての項目を入力してください。</p>`;
      return;
    }

    // 仮追加（今後localStorage連携可能）
    messageArea.innerHTML = `
      <p class="success">「${name}（${amount}${unit}）」を冷蔵庫に追加しました！</p>
    `;

    // 入力欄をクリア
    foodForm.reset();
  });
});
