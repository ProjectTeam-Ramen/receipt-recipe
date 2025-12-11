// ==============================
// 食材削除ページ (food-delete.js)
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const deleteForm = document.getElementById("deleteForm");
  const deleteMessage = document.getElementById("deleteMessage");

  // 戻るボタンで管理ページに戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-control.html";
  });

  // 食材削除フォーム送信処理
  deleteForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = document.getElementById("deleteName").value.trim();

    if (!name) {
      deleteMessage.innerHTML = `<p class="error">食材名を入力してください。</p>`;
      return;
    }

    // 今後localStorage連携可能。仮メッセージ表示
    deleteMessage.innerHTML = `
      <p class="success">「${name}」を冷蔵庫から削除しました。</p>
    `;

    // 入力リセット
    deleteForm.reset();
  });
});
