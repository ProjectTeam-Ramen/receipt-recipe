const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
};

document.addEventListener("DOMContentLoaded", () => {
  const foodList = document.getElementById("foodList");

  if (!localStorage.getItem(STORAGE_KEYS.refreshToken)) {
    redirectToLogin();
    return;
  }

  loadFoods();

  async function loadFoods() {
    foodList.innerHTML = `<tr><td colspan="6">読み込み中...</td></tr>`;
    try {
      const token = await ensureValidAccessToken();
      const [unusedItems, usedItems] = await Promise.all([
        fetchIngredientList(token, "unused"),
        fetchIngredientList(token, "used"),
      ]);
      const items = [...unusedItems, ...usedItems];

      if (!items.length) {
        foodList.innerHTML = `<tr><td colspan="6">冷蔵庫に食材が登録されていません。</td></tr>`;
        return;
      }

      renderIngredientRows(items);
      attachUseHandlers();
      attachDeleteHandlers();
    } catch (error) {
      console.error("データ取得エラー", error);
      foodList.innerHTML = `<tr><td colspan="6">データの取得に失敗しました。</td></tr>`;
    }
  }

  function renderIngredientRows(items) {
    foodList.innerHTML = "";
    items.forEach((item) => {
      const disabled = item.status === "deleted";
      const quantityValue = Number(item.quantity_g ?? 0);
      const isConsumed = quantityValue <= 0;
      const tr = document.createElement("tr");

      tr.appendChild(createCell(item.food_name));
      tr.appendChild(createCell(formatQuantity(item.quantity_g)));
      tr.appendChild(createCell(item.purchase_date || "-"));
      tr.appendChild(createCell(item.expiration_date || "-"));
      tr.appendChild(createCell(formatStatus(item)));

      const actionsCell = document.createElement("td");
      actionsCell.classList.add("actions-cell");

      const useButton = createActionButton(
        "use-btn",
        "使用",
        item,
        disabled || isConsumed,
      );
      useButton.dataset.quantity = String(quantityValue);
      useButton.dataset.status = item.status ?? "unused";
      const deleteButton = createActionButton("delete-btn", "削除", item, disabled);

      actionsCell.appendChild(useButton);
      actionsCell.appendChild(deleteButton);
      tr.appendChild(actionsCell);

      foodList.appendChild(tr);
    });
  }

  function attachUseHandlers() {
    foodList.querySelectorAll(".use-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const userFoodId = button.dataset.id;
        const foodName = button.dataset.name || "この食材";
        const quantityValue = Number(button.dataset.quantity) || 0;
        if (!userFoodId || quantityValue <= 0) return;
        const defaultSuggestion = quantityValue > 0 ? Math.min(quantityValue, 50) : "";
        const promptValue = window.prompt(
          `${foodName} の使用量 (g) を入力してください`,
          defaultSuggestion ? String(defaultSuggestion) : "",
        );
        if (promptValue === null) return;
        const amount = Number(promptValue);
        if (!Number.isFinite(amount) || amount <= 0) {
          alert("正しい数量(g)を入力してください。");
          return;
        }
        if (amount > quantityValue) {
          alert(`在庫(${quantityValue} g)を超える数量は指定できません。`);
          return;
        }
        try {
          const token = await ensureValidAccessToken();
          const response = await fetch(
            `${API_BASE_URL}/ingredients/${userFoodId}/consume`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({ quantity_g: amount }),
            },
          );
          const data = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(data?.detail || "使用処理に失敗しました。");
          }
          loadFoods();
        } catch (error) {
          console.error("使用処理エラー", error);
          alert(error.message || "食材の更新に失敗しました。");
        }
      });
    });
  }

  async function fetchIngredientList(token, status) {
    const baseUrl = `${API_BASE_URL}/ingredients`;
    const url = status ? `${baseUrl}?status=${status}` : baseUrl;
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) {
        clearSession();
        redirectToLogin();
        return [];
      }
      throw new Error(data?.detail || "食材一覧の取得に失敗しました。");
    }
    return data?.ingredients ?? [];
  }

  function attachDeleteHandlers() {
    foodList.querySelectorAll(".delete-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const userFoodId = button.dataset.id;
        const foodName = button.dataset.name;
        if (!userFoodId || !foodName) return;
        const confirmed = window.confirm(
          `${foodName} を削除します。よろしいですか？（在庫使用とは別処理です）`,
        );
        if (!confirmed) return;

        try {
          const token = await ensureValidAccessToken();
          const response = await fetch(
            `${API_BASE_URL}/ingredients/${userFoodId}`,
            {
              method: "DELETE",
              headers: { Authorization: `Bearer ${token}` },
            },
          );
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data?.detail || "削除に失敗しました。");
          }
          loadFoods();
        } catch (error) {
          console.error("削除処理エラー", error);
          alert(error.message || "削除処理に失敗しました。");
        }
      });
    });
  }

  function formatStatus(item) {
    const status = item.status;
    const quantityValue = Number(item.quantity_g ?? 0);
    if (status === "used") {
      return quantityValue <= 0 ? "使用済" : "使用中";
    }
    if (status === "deleted") {
      return "削除済";
    }
    return "未使用";
  }

  function formatQuantity(quantity) {
    if (quantity === null || quantity === undefined || quantity === "") {
      return "-";
    }
    const numeric = Number(quantity);
    if (Number.isFinite(numeric)) {
      return `${numeric} g`;
    }
    return `${quantity} g`;
  }

  function createCell(text) {
    const td = document.createElement("td");
    if (text === null || text === undefined || text === "") {
      td.textContent = "-";
    } else {
      td.textContent = String(text);
    }
    return td;
  }

  function createActionButton(className, label, item, disabled) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.dataset.id = String(item.user_food_id);
    button.dataset.name = item.food_name ?? "";
    const numericQuantity = Number(item.quantity_g ?? 0);
    button.dataset.quantity = Number.isFinite(numericQuantity)
      ? String(numericQuantity)
      : String(item.quantity_g ?? "0");
    button.dataset.status = item.status ?? "unused";
    if (disabled) {
      button.disabled = true;
    }
    return button;
  }
});

function redirectToLogin() {
  window.location.href = "index.html";
}

function clearSession() {
  Object.values(STORAGE_KEYS).forEach((key) => {
    if (typeof key === "string") {
      localStorage.removeItem(key);
    }
  });
}

async function ensureValidAccessToken() {
  const accessKey = STORAGE_KEYS.accessToken;
  const refreshKey = STORAGE_KEYS.refreshToken;
  const expiresKey = STORAGE_KEYS.accessTokenExpiresAt;
  const expiresAt = Number(localStorage.getItem(expiresKey) || 0);
  const refreshToken = localStorage.getItem(refreshKey);
  let accessToken = localStorage.getItem(accessKey);

  if (accessToken && Date.now() < expiresAt - 5000) {
    return accessToken;
  }

  if (!refreshToken) {
    throw new Error("ログインの有効期限が切れています。");
  }

  return refreshAccessToken(refreshToken);
}

async function refreshAccessToken(refreshToken) {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) {
    clearSession();
    throw new Error(data?.detail || "トークンの更新に失敗しました。");
  }

  const accessKey = STORAGE_KEYS.accessToken;
  const expiresKey = STORAGE_KEYS.accessTokenExpiresAt;
  const expiresInMs = Number(data.expires_in ?? 1800) * 1000;
  localStorage.setItem(accessKey, data.access_token);
  localStorage.setItem(expiresKey, String(Date.now() + expiresInMs));
  return data.access_token;
}
