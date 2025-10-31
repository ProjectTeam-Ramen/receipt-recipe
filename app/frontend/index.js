document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  const message = document.getElementById("message");

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const username = form.username.value.trim();
    const password = form.password.value.trim();

    // 簡単なデモ用の認証（本番ではサーバー側で処理）
    if (username === "user" && password === "pass123") {
      message.style.color = "green";
      message.textContent = "ログイン成功！";
      setTimeout(() => {
        window.location.href = "home.html"; // 次のページへ
      }, 1000);
    } else {
      message.style.color = "red";
      message.textContent = "ユーザー名またはパスワードが違います。";
    }
  });
});
