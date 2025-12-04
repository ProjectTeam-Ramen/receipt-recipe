// ▼ ダミー OCR 結果（実際はOCR処理の結果をここに入れる）
function mockOCR() {
  return [
    { name: "牛乳", date: "2025-02-01" },
    { name: "鶏肉", date: "2025-02-01" },
    { name: "たまご", date: "2025-02-01" }
  ];
}

document.getElementById("scanBtn").addEventListener("click", () => {
  document.getElementById("scanMessage").textContent = "読み取り中...";
  
  // OCR処理（ダミー）
  const result = mockOCR();

  document.getElementById("scanMessage").textContent =
    `${result.length} 件の食材を検出しました`;
  
  displayForms(result);
});

// ▼ フォームを横並びで表示
function displayForms(items) {
  const container = document.getElementById("formsContainer");
  container.innerHTML = "";

  items.forEach((item, index) => {
    const form = document.createElement("div");
    form.classList.add("food-form");

    form.innerHTML = `
      <label>食材名</label>
      <input type="text" id="foodName_${index}" value="${item.name}">

      <label>数量(g)</label>
      <input type="number" id="quantity_${index}">

      <label>購入日</label>
      <input type="date" id="purchaseDate_${index}" value="${item.date}">

      <label>賞味期限</label>
      <input type="date" id="expireDate_${index}">
    `;
    container.appendChild(form);
  });

  document.getElementById("registerBtn").style.display = "block";
}

// ▼ すべて登録する
document.getElementById("registerBtn").addEventListener("click", async () => {
  const forms = document.querySelectorAll(".food-form");
  const dataToSend = [];

  forms.forEach((_, index) => {
    dataToSend.push({
      food_name: document.getElementById(`foodName_${index}`).value,
      quantity: document.getElementById(`quantity_${index}`).value,
      purchase_date: document.getElementById(`purchaseDate_${index}`).value,
      expiration_date: document.getElementById(`expireDate_${index}`).value,
      user_id: 1
    });
  });

  console.log("送信データ:", dataToSend);

  for (const d of dataToSend) {
    await fetch("http://localhost:5500/api/add-food", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(d),
    });
  }

  alert("登録が完了しました！");
});

// ▼ 戻るボタン（共通処理）
document.getElementById("backBtn").addEventListener("click", () => {
  window.location.href = "fridge-control.html";
});
