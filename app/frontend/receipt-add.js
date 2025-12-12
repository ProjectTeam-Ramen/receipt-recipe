const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const STORAGE_KEYS = window.APP_CONFIG?.storageKeys ?? {
  accessToken: "rr.access_token",
  refreshToken: "rr.refresh_token",
  accessTokenExpiresAt: "rr.access_token_expires_at",
};

document.addEventListener("DOMContentLoaded", () => {
  const receiptInput = document.getElementById("receiptInput");
  const scanBtn = document.getElementById("scanBtn");
  const scanMessage = document.getElementById("scanMessage");
  const statusBadge = document.getElementById("statusBadge");
  const statusMessage = document.getElementById("statusMessage");
  const refreshStatusBtn = document.getElementById("refreshStatusBtn");
  const receiptMeta = document.getElementById("receiptMeta");
  const receiptIdLabel = document.getElementById("receiptIdLabel");
  const receiptUpdatedAt = document.getElementById("receiptUpdatedAt");
  const textSection = document.getElementById("textResultSection");
  const textOutput = document.getElementById("receiptTextOutput");
  const copyTextBtn = document.getElementById("copyTextBtn");
  const downloadTextLink = document.getElementById("downloadTextLink");
  const linesSection = document.getElementById("linesSection");
  const linesContainer = document.getElementById("linesContainer");
  const linesEmptyMessage = document.getElementById("linesEmptyMessage");
  const backBtn = document.getElementById("backBtn");

  let currentReceiptId = null;
  let pollingHandle = null;

  if (!localStorage.getItem(STORAGE_KEYS.refreshToken)) {
    redirectToLogin();
    return;
  }

  backBtn?.addEventListener("click", () => {
    window.location.href = "fridge-control.html";
  });

  scanBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    handleUpload();
  });

  refreshStatusBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    if (currentReceiptId) {
      checkReceiptStatus(currentReceiptId, { immediate: true });
    }
  });

  copyTextBtn?.addEventListener("click", async () => {
    const text = textOutput?.textContent ?? "";
    if (!text.trim()) {
      setStatusMessage("コピーできるテキストがまだありません。", "warn");
      return;
    }
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "true");
        textarea.style.position = "absolute";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setStatusMessage("テキストをクリップボードにコピーしました。", "success");
    } catch (error) {
      console.error(error);
      setStatusMessage("テキストのコピーに失敗しました。", "error");
    }
  });

  window.addEventListener("beforeunload", () => {
    if (pollingHandle) {
      clearInterval(pollingHandle);
    }
  });

  initializeState();

  async function handleUpload() {
    if (!receiptInput?.files?.length) {
      setScanMessage("レシート画像を選択してください。", "error");
      return;
    }

    const file = receiptInput.files[0];
    if (!file) {
      setScanMessage("ファイルの読み込みに失敗しました。", "error");
      return;
    }

    resetResults();
    setScanMessage("アップロード中です...", "info");
    setStatusBadge("processing");
    setStatusMessage("OCRを実行しています。完了までしばらくお待ちください。", "info");
    scanBtn.disabled = true;

    try {
      const token = await ensureValidAccessToken();
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/receipts/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: formData,
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        handleAuthError(response.status);
        throw new Error(data?.detail || "レシートのアップロードに失敗しました。");
      }

      currentReceiptId = data.receipt_id;
      updateReceiptMeta({
        receipt_id: currentReceiptId,
        updated_at: data.updated_at || new Date().toISOString(),
      });
      toggleElement(receiptMeta, true);
      toggleRefreshButton();
      startPolling(currentReceiptId);
    } catch (error) {
      console.error(error);
      setStatusBadge("failed");
      setStatusMessage(error.message || "アップロードに失敗しました。", "error");
    } finally {
      scanBtn.disabled = false;
    }
  }

  function startPolling(receiptId) {
    if (pollingHandle) {
      clearInterval(pollingHandle);
    }
    pollingHandle = setInterval(() => checkReceiptStatus(receiptId), 2500);
    checkReceiptStatus(receiptId, { immediate: true });
  }

  async function checkReceiptStatus(receiptId, { immediate = false } = {}) {
    try {
      const token = await ensureValidAccessToken();
      const response = await fetch(`${API_BASE_URL}/receipts/${receiptId}/status`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        handleAuthError(response.status);
        throw new Error(data?.detail || "処理状況の取得に失敗しました。");
      }

      const status = data.status || "processing";
      updateReceiptMeta({ receipt_id: receiptId, updated_at: data.updated_at });
      toggleElement(receiptMeta, true);
      setStatusBadge(status);

      if (status === "completed") {
        setStatusMessage("OCRが完了しました。結果を読み込んでいます。", "success");
        clearInterval(pollingHandle);
        pollingHandle = null;
        await Promise.all([
          loadReceiptText(receiptId),
          loadReceiptDetails(receiptId),
        ]);
      } else if (status === "failed") {
        clearInterval(pollingHandle);
        pollingHandle = null;
        const errorMessage = data.error || "OCR処理に失敗しました。";
        setStatusMessage(errorMessage, "error");
      } else if (immediate) {
        setStatusMessage("OCRを実行しています。完了まで少々お待ちください。", "info");
      }
    } catch (error) {
      console.error(error);
      setStatusMessage(error.message || "処理状況の取得に失敗しました。", "error");
    }
  }

  async function loadReceiptText(receiptId) {
    const token = await ensureValidAccessToken();
    const response = await fetch(`${API_BASE_URL}/receipts/${receiptId}/text`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      handleAuthError(response.status);
      throw new Error(data?.detail || "テキストの取得に失敗しました。");
    }

    const text = (data.text || "").trim();
    textOutput.textContent = text || "テキストを抽出できませんでした。";
    toggleElement(textSection, true);
    updateDownloadLink(receiptId, Boolean(text));
  }

  async function loadReceiptDetails(receiptId) {
    const token = await ensureValidAccessToken();
    const response = await fetch(`${API_BASE_URL}/receipts/${receiptId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      handleAuthError(response.status);
      throw new Error(data?.detail || "詳細情報の取得に失敗しました。");
    }

    updateReceiptMeta(data);
    toggleElement(receiptMeta, true);
    const lines = Array.isArray(data.text_lines) ? data.text_lines : [];
    renderLineCards(lines);
  }

  function renderLineCards(lines) {
    if (!linesContainer) return;
    linesContainer.innerHTML = "";
    if (!lines.length) {
      linesEmptyMessage?.classList.remove("hidden");
      return;
    }

    linesEmptyMessage?.classList.add("hidden");
    lines.forEach((line) => {
      const card = document.createElement("article");
      card.className = "line-card";

      const header = document.createElement("div");
      header.className = "line-card-header";
      const lineId = typeof line.line_id === "number" ? line.line_id : "-";
      header.innerHTML = `
        <span>行 ${lineId}</span>
        <span class="confidence-chip">${formatConfidence(line.confidence)}</span>
      `;

      const body = document.createElement("p");
      body.className = "line-card-text";
      body.textContent = line.text || "(空行)";

      const metaList = document.createElement("dl");
      metaList.className = "line-card-meta";
      const bbox = formatBBox(line.bbox);
      const center = formatPoint(line.center);
      metaList.innerHTML = `
        <div>
          <dt>中心座標</dt>
          <dd>${center}</dd>
        </div>
        <div>
          <dt>バウンディングボックス</dt>
          <dd>${bbox}</dd>
        </div>
      `;

      card.appendChild(header);
      card.appendChild(body);
      card.appendChild(metaList);
      linesContainer.appendChild(card);
    });
  }

  function resetResults() {
    textOutput.textContent = "";
    toggleElement(textSection, false);
    updateDownloadLink(null, false);
    if (linesContainer) {
      linesContainer.innerHTML = "";
    }
    linesEmptyMessage?.classList.remove("hidden");
  }

  function initializeState() {
    setStatusBadge("idle");
    setStatusMessage("まだ処理は開始されていません。", "info");
    toggleElement(textSection, false);
    toggleElement(receiptMeta, false);
    toggleRefreshButton();
  }

  function toggleRefreshButton() {
    if (!refreshStatusBtn) return;
    refreshStatusBtn.disabled = !currentReceiptId;
  }

  function updateReceiptMeta(meta = {}) {
    if (!receiptMeta) return;
    if (meta.receipt_id) {
      receiptIdLabel.textContent = `#${meta.receipt_id}`;
    }
    if (meta.updated_at) {
      receiptUpdatedAt.textContent = formatDate(meta.updated_at);
    }
  }

  function updateDownloadLink(receiptId, enabled) {
    if (!downloadTextLink) return;
    if (enabled && receiptId) {
      downloadTextLink.href = `${API_BASE_URL}/receipts/${receiptId}/text?format=plain`;
      downloadTextLink.setAttribute("aria-disabled", "false");
    } else {
      downloadTextLink.href = "#";
      downloadTextLink.setAttribute("aria-disabled", "true");
    }
  }

  function setScanMessage(text, type = "info") {
    if (!scanMessage) return;
    scanMessage.textContent = text;
    scanMessage.className = `status-hint status-${type}`;
  }

  function setStatusMessage(text, type = "info") {
    if (!statusMessage) return;
    statusMessage.textContent = text;
    statusMessage.className = `status-message status-${type}`;
  }

  function setStatusBadge(state) {
    if (!statusBadge) return;
    const labelMap = {
      idle: "待機中",
      processing: "処理中",
      completed: "完了",
      failed: "失敗",
    };
    const normalized = labelMap[state] ? state : "idle";
    statusBadge.textContent = labelMap[normalized];
    statusBadge.className = `status-pill status-${normalized}`;
  }

  function toggleElement(element, shouldShow) {
    if (!element) return;
    element.classList.toggle("hidden", !shouldShow);
  }

  function formatConfidence(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "-";
    }
    const percentage = Math.round(value * 100);
    return `${percentage}%`;
  }

  function formatPoint(point) {
    if (!Array.isArray(point) || point.length !== 2) {
      return "-";
    }
    const [x, y] = point.map((num) => Number(num).toFixed(1));
    return `${x}, ${y}`;
  }

  function formatBBox(bbox) {
    if (!Array.isArray(bbox) || !bbox.length) {
      return "-";
    }
    return bbox
      .map((pair) =>
        Array.isArray(pair) && pair.length === 2
          ? `(${Number(pair[0]).toFixed(1)}, ${Number(pair[1]).toFixed(1)})`
          : "-",
      )
      .join(" / ");
  }

  function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }

  function handleAuthError(status) {
    if (status === 401) {
      clearSession();
      redirectToLogin();
    }
  }
});

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
  const currentToken = localStorage.getItem(accessKey);

  if (currentToken && Date.now() < expiresAt - 5000) {
    return currentToken;
  }

  if (!refreshToken) {
    throw new Error("ログインの有効期限が切れています。再度ログインしてください。");
  }

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

  const expiresIn = Number(data.expires_in ?? 1800) * 1000;
  localStorage.setItem(accessKey, data.access_token);
  localStorage.setItem(expiresKey, String(Date.now() + expiresIn));
  return data.access_token;
}

function redirectToLogin() {
  window.location.href = "index.html";
}
