const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("registerForm");
  const message = document.getElementById("message");
  const submitBtn = form.querySelector("button[type='submit']");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.textContent = "";

    const username = form.username.value.trim();
    const email = form.email.value.trim().toLowerCase();
    const password = form.password.value;
    const passwordConfirm = form.passwordConfirm.value;
    const birthdayRaw = form.birthday.value;

    if (password !== passwordConfirm) {
      setMessage("パスワードが一致しません。", "error");
      return;
    }
    if (!username || !email || !password) {
      setMessage("必須項目を入力してください。", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "送信中...";

    const payload = {
      username,
      email,
      password,
      birthday: birthdayRaw || null,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.detail || "登録に失敗しました。");
      }
      setMessage("登録が完了しました。ログイン画面へ移動します。", "success");
      setTimeout(() => {
        window.location.href = "index.html";
      }, 1000);
    } catch (error) {
      console.error(error);
      setMessage(error.message || "登録に失敗しました。", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "登録する";
    }
  });

  function setMessage(text, type) {
    message.textContent = text;
    message.style.color = type === "success" ? "#15803d" : "#dc2626";
  }
});
