// ==============================
// 冷蔵庫管理ページ (fridge-control.js)
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const addFoodBtn = document.getElementById("addFoodBtn");
  const deleteFoodBtn = document.getElementById("deleteFoodBtn");
  const receiptAddBtn = document.getElementById("receiptAddBtn");

  // 戻るボタン → fridge-home.htmlへ戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-home.html";
  });

  // 食材追加ページへ移動
  addFoodBtn.addEventListener("click", () => {
    window.location.href = "food-add.html";
  });

  // レシート読み取りページへ移動
  receiptAddBtn.addEventListener("click", () => {
    window.location.href = "receipt-add.html";
  });
});
