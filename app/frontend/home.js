document.addEventListener("DOMContentLoaded", () => {
  const logoutBtn = document.getElementById("logoutBtn");
  const welcomeMsg = document.getElementById("welcomeMsg");

  // ログイン時のユーザー名を保存している想定
  const username = localStorage.getItem("username") || "ゲスト";
  welcomeMsg.textContent = `${username} さんでログイン中です。`;

  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("username");
    alert("ログアウトしました。");
    window.location.href = "index.html";
  });
});
