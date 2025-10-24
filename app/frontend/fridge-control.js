// ==============================
// 冷蔵庫：食材追加・削除ページ用スクリプト
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const addForm = document.getElementById("addForm");
  const ingredientInput = document.getElementById("ingredientInput");
  const ingredientList = document.getElementById("ingredientList");

  let ingredients = []; // 簡易的に配列で保持（今後localStorage対応も可）

  // 冷蔵庫ホームに戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-home.html";
  });

  // 食材追加処理
  addForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const ingredient = ingredientInput.value.trim();
    if (ingredient === "") return;

    ingredients.push(ingredient);
    ingredientInput.value = "";
    renderList();
  });

  // 食材削除処理
  function deleteIngredient(index) {
    ingredients.splice(index, 1);
    renderList();
  }

  // 食材一覧描画
  function renderList() {
    if (ingredients.length === 0) {
      ingredientList.innerHTML = `<p>現在、登録されている食材はありません。</p>`;
      return;
    }

    ingredientList.innerHTML = ingredients
      .map(
        (item, index) => `
        <div class="ingredient-item">
          <span>${item}</span>
          <button class="delete-btn" onclick="deleteIngredient(${index})">削除</button>
        </div>`
      )
      .join("");
  }

  // deleteIngredientをグローバルスコープに登録（HTMLから呼べるように）
  window.deleteIngredient = deleteIngredient;
});
