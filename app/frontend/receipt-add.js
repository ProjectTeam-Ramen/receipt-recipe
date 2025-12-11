// ==============================
// レシート読み取りページ
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.getElementById("backBtn");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const resultArea = document.getElementById("resultArea");
  const receiptInput = document.getElementById("receiptInput");

  // 戻るボタンで管理ページへ戻る
  backBtn.addEventListener("click", () => {
    window.location.href = "fridge-control.html";
  });

  // 仮のレシート解析処理
  analyzeBtn.addEventListener("click", () => {
    const file = receiptInput.files[0];
    if (!file) {
      alert("レシート画像を選択してください。");
      return;
    }

    // 今後OCR処理を実装予定（現段階ではダミー）
    setTimeout(() => {
      const dummyIngredients = ["キャベツ", "牛乳", "豚肉"];
      resultArea.innerHTML = `
        <h3>検出された食材:</h3>
        <ul>
          ${dummyIngredients.map(item => `<li>${item}</li>`).join("")}
        </ul>
        <p>これらの食材を冷蔵庫に追加しますか？</p>
        <button id="confirmAddBtn" class="confirm-btn">追加する</button>
      `;

      document.getElementById("confirmAddBtn").addEventListener("click", () => {
        alert("食材を冷蔵庫に追加しました！（仮実装）");
      });
    }, 1000);
  });
});
