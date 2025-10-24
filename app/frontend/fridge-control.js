// ==============================
// 冷蔵庫管理ページ (fridge-control.js)
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const addPageBtn = document.getElementById("addPageBtn");
  const deletePageBtn = document.getElementById("deletePageBtn");
  const receiptBtn = document.getElementById("receiptBtn");

  // 冷蔵庫ホーム画面へ戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-home.html";
  });

  // 食材追加ページへ移動
  addPageBtn.addEventListener("click", () => {
    // ここは今後 "fridge-add.html" などのページを作成した際に変更可能
    alert("食材追加ページへ移動（今後実装予定）");
    // window.location.href = "fridge-add.html";
  });

  // 食材削除ページへ移動
  deletePageBtn.addEventListener("click", () => {
    alert("食材削除ページへ移動（今後実装予定）");
    // window.location.href = "fridge-delete.html";
  });

  // レシートから追加ページへ移動
  receiptBtn.addEventListener("click", () => {
    window.location.href = "receipt-add.html";
  });
});
