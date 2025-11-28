document.addEventListener("DOMContentLoaded", async () => {
  const foodList = document.getElementById("foodList");

  try {
    // ★ ログイン中ユーザー（仮設定）
    const userId = 1;

    // APIからデータ取得
    const response = await fetch(`http://localhost:5502/api/user-foods?user_id=${userId}`);

    if (!response.ok) {
      throw new Error(`サーバーエラー: ${response.status}`);
    }

    const data = await response.json();

    // データが空の場合
    if (!data || data.length === 0) {
      foodList.innerHTML = `<tr><td colspan="5">冷蔵庫に食材が登録されていません。</td></tr>`;
      return;
    }

    // テーブル出力
    foodList.innerHTML = data
      .map(
        (item) => `
        <tr>
          <td>${item.food_name}</td>
          <td>${item.quantity}</td>
          <td>${item.purchase_date || "-"}</td>
          <td>${item.expiration_date || "-"}</td>
        </tr>`
      )
      .join("");
  } catch (error) {
    console.error("データ取得エラー:", error);
    foodList.innerHTML = `<tr><td colspan="5">データの取得に失敗しました。</td></tr>`;
  }
});
