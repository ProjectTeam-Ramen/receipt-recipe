const API_BASE_URL = window.APP_CONFIG?.apiBaseUrl ?? "http://127.0.0.1:8000/api/v1";
const FOOD_OPTIONS_LIMIT = 500;
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
  const itemsSection = document.getElementById("itemsSection");
  const itemsContainer = document.getElementById("itemsContainer");
  const itemsEmptyMessage = document.getElementById("itemsEmptyMessage");
  const backBtn = document.getElementById("backBtn");

  let currentReceiptId = null;
  let pollingHandle = null;
  let hiddenItemIds = new Set();
  let foodOptions = [];
  let foodOptionsLoaded = false;
  let foodOptionsError = null;
  let foodOptionsPromise = null;

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
  setupSectionToggleButtons();

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
    const items = Array.isArray(data.items) ? data.items : [];
    // load per-receipt hidden item ids from localStorage
    hiddenItemIds = loadHiddenItemsForReceipt(receiptId);
    try {
      await ensureFoodOptions();
    } catch (error) {
      console.warn("食材候補の取得に失敗しました", error);
    }
    renderLineCards(lines);
    renderItemCards(items);
  }

  async function ensureFoodOptions(force = false) {
    if (foodOptionsLoaded && !force) {
      return foodOptions;
    }
    if (!foodOptionsPromise || force) {
      foodOptionsPromise = (async () => {
        try {
          const token = await ensureValidAccessToken();
          const response = await fetch(
            `${API_BASE_URL}/receipts/food-options?limit=${FOOD_OPTIONS_LIMIT}`,
            {
              headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            },
          );
          const data = await response.json().catch(() => []);
          if (!response.ok) {
            handleAuthError(response.status);
            throw new Error(
              data?.detail || "食材候補の取得に失敗しました。",
            );
          }
          foodOptions = Array.isArray(data) ? data : [];
          foodOptionsLoaded = true;
          foodOptionsError = null;
          return foodOptions;
        } catch (error) {
          foodOptionsLoaded = false;
          foodOptions = [];
          foodOptionsError = error;
          foodOptionsPromise = null;
          throw error;
        }
      })();
    }
    return foodOptionsPromise;
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

  function renderItemCards(items) {
    if (!itemsSection || !itemsContainer) return;
    itemsContainer.innerHTML = "";
    toggleElement(itemsSection, true);

    if (!Array.isArray(items) || !items.length) {
      itemsEmptyMessage?.classList.remove("hidden");
      return;
    }

    itemsEmptyMessage?.classList.add("hidden");
    items.forEach((item) => {
      // skip items explicitly hidden by user for this receipt
      const id = item?.item_id;
      if (id && hiddenItemIds && hiddenItemIds.has(id)) return;
      const card = document.createElement("article");
      card.className = "item-card";
      const hideCard = () => {
        // persist hidden state and remove card
        try {
          markItemHidden(currentReceiptId, item?.item_id);
        } catch (e) {
          console.warn('mark hidden failed', e);
        }
        hideItemCard(card);
      };

      const resolution = item?.ingredient_resolution ?? null;
      const resolvedName = item?.food_name || "未解決";
      const resolvedState = item?.food_name ? "resolved" : "unresolved";
      const confidenceValue = resolution?.confidence ?? item?.confidence;

      const header = document.createElement("div");
      header.className = "item-card-header";
      header.innerHTML = `
        <span>アイテム ${item?.item_id ?? "-"}</span>
        <span class="confidence-chip">${formatConfidence(confidenceValue)}</span>
      `;

      const raw = document.createElement("p");
      raw.className = "item-raw-text";
      raw.textContent = item?.raw_text || "(テキストなし)";

      const resolved = document.createElement("div");
      resolved.className = `item-resolved ${resolvedState}`;
      resolved.innerHTML = `
        <span class="item-label">抽象化</span>
        <strong>${resolvedName}</strong>
      `;

      const metaList = document.createElement("dl");
      metaList.className = "item-meta";
      metaList.innerHTML = `
        <div>
          <dt>正規化テキスト</dt>
          <dd>${resolution?.normalized_text || "-"}</dd>
        </div>
        <div>
          <dt>解決ソース</dt>
          <dd>${resolution?.source || "-"}</dd>
        </div>
        <div>
          <dt>キャッシュ</dt>
          <dd>${formatYesNo(resolution?.cached)}</dd>
        </div>
      `;

      card.appendChild(header);
      card.appendChild(raw);
      card.appendChild(resolved);
      card.appendChild(metaList);

      const quickFridgeSection = buildQuickFridgeControls(item, resolvedName, {
        onFridgeSuccess: hideCard,
      });
      if (quickFridgeSection) {
        card.appendChild(quickFridgeSection);
      }

      const predictions = Array.isArray(resolution?.metadata?.predictions)
        ? resolution.metadata.predictions
        : [];
      if (predictions.length) {
        const list = document.createElement("ul");
        list.className = "item-predictions";
        predictions.slice(0, 3).forEach((prediction) => {
          const li = document.createElement("li");
          const label = prediction?.food_name || prediction?.label || "候補";
          li.innerHTML = `
            <span>${label}</span>
            <span class="confidence-chip">${formatConfidence(prediction?.probability)}</span>
          `;
          list.appendChild(li);
        });
        card.appendChild(list);
      }

      const actions = document.createElement("div");
      actions.className = "item-actions";
      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "ghost-btn item-edit-btn";
      editButton.textContent = "手動で修正";
      actions.appendChild(editButton);

      const hideButton = document.createElement("button");
      hideButton.type = "button";
      hideButton.className = "ghost-btn item-hide-btn";
      hideButton.textContent = "非表示";
      hideButton.addEventListener("click", hideCard);
      actions.appendChild(hideButton);

      card.appendChild(actions);

      const correctionForm = buildManualCorrectionForm(item, resolvedName, {
        onFridgeSuccess: hideCard,
      });
      card.appendChild(correctionForm);

      editButton.addEventListener("click", () => {
        correctionForm.classList.toggle("hidden");
        if (!correctionForm.classList.contains("hidden")) {
          const rawField = correctionForm.querySelector('[name="raw_text"]');
          rawField?.focus();
        }
      });

      itemsContainer.appendChild(card);
    });
  }

  function buildManualCorrectionForm(item, resolvedName, options = {}) {
    const { onFridgeSuccess } = options;
    const form = document.createElement("form");
    form.className = "item-correction-form hidden";

    const rawLabel = document.createElement("label");
    rawLabel.textContent = "認識テキスト";
    const rawInput = document.createElement("textarea");
    rawInput.name = "raw_text";
    rawInput.rows = 2;
    rawInput.value = item?.raw_text || "";
    rawLabel.appendChild(rawInput);
    form.appendChild(rawLabel);

    const resolvedLabel = document.createElement("label");
    resolvedLabel.textContent = "正しい食材名";
    const resolvedSelect = document.createElement("select");
    resolvedSelect.name = "resolved_food_name";
    resolvedSelect.required = true;
    resolvedLabel.appendChild(resolvedSelect);
    form.appendChild(resolvedLabel);
    populateFoodSelectOptions(resolvedSelect, item?.food_id, resolvedName);
    resolvedSelect.disabled = !foodOptions.length;

    if (!foodOptions.length) {
      const warningWrapper = document.createElement("div");
      warningWrapper.className = "food-options-warning";

      const warning = document.createElement("p");
      warning.className = "item-correction-status warn";
      let warningText = "利用可能な食材候補がありません。食材マスタに食材を登録してください。";
      if (foodOptionsError) {
        if (typeof foodOptionsError === "string") {
          warningText = foodOptionsError;
        } else {
          try {
            warningText = JSON.stringify(foodOptionsError);
          } catch (e) {
            warningText = String(foodOptionsError);
          }
        }
      }
      warning.textContent = warningText;
      warningWrapper.appendChild(warning);

      const retryButton = document.createElement("button");
      retryButton.type = "button";
      retryButton.className = "ghost-btn";
      retryButton.textContent = "候補を再取得";
      retryButton.addEventListener("click", () =>
        handleFoodOptionReload({
          selectEl: resolvedSelect,
          warningEl: warning,
          defaultFoodId: item?.food_id,
          fallbackName: resolvedName,
          buttonEl: retryButton,
        }),
      );
      warningWrapper.appendChild(retryButton);

      form.appendChild(warningWrapper);
    }

    const noteLabel = document.createElement("label");
    noteLabel.textContent = "メモ";
    const noteInput = document.createElement("textarea");
    noteInput.name = "note";
    noteInput.rows = 2;
    noteLabel.appendChild(noteInput);
    form.appendChild(noteLabel);

    const fridgeSection = document.createElement("section");
    fridgeSection.className = "item-fridge-section";
    const fridgeTitle = document.createElement("h4");
    fridgeTitle.textContent = "冷蔵庫に登録";
    fridgeSection.appendChild(fridgeTitle);

    const fridgeLabel = document.createElement("label");
    fridgeLabel.textContent = "重量 (g)";
    const fridgeInput = document.createElement("input");
    fridgeInput.type = "number";
    fridgeInput.name = "fridge_quantity_g";
    fridgeInput.min = "1";
    fridgeInput.step = "1";
    fridgeInput.placeholder = "例: 120";
    fridgeLabel.appendChild(fridgeInput);
    fridgeSection.appendChild(fridgeLabel);

    const expirationLabel = document.createElement("label");
    expirationLabel.textContent = "賞味期限";
    const expirationInput = document.createElement("input");
    expirationInput.type = "date";
    expirationInput.name = "fridge_expiration_date";
    expirationLabel.appendChild(expirationInput);
    fridgeSection.appendChild(expirationLabel);

    const fridgeActions = document.createElement("div");
    fridgeActions.className = "item-fridge-actions";
    const fridgeButton = document.createElement("button");
    fridgeButton.type = "button";
    fridgeButton.className = "secondary-btn";
    fridgeButton.textContent = "冷蔵庫へ登録";
    fridgeActions.appendChild(fridgeButton);
    fridgeSection.appendChild(fridgeActions);

    const fridgeStatus = document.createElement("p");
    fridgeStatus.className = "item-fridge-status";
    fridgeStatus.setAttribute("aria-live", "polite");
    fridgeSection.appendChild(fridgeStatus);

    fridgeButton.addEventListener("click", () =>
      handleAddIngredientToFridge({
        selectEl: resolvedSelect,
        quantityInput: fridgeInput,
        expirationInput,
        statusTarget: fridgeStatus,
        triggerButton: fridgeButton,
        onSuccess: onFridgeSuccess,
      }),
    );

    form.appendChild(fridgeSection);

    const actionRow = document.createElement("div");
    actionRow.className = "item-correction-actions";
    const saveButton = document.createElement("button");
    saveButton.type = "submit";
    saveButton.textContent = "保存";
    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "ghost-btn";
    cancelButton.dataset.action = "cancel";
    cancelButton.textContent = "キャンセル";
    actionRow.appendChild(saveButton);
    actionRow.appendChild(cancelButton);
    form.appendChild(actionRow);

    const status = document.createElement("p");
    status.className = "item-correction-status";
    status.setAttribute("aria-live", "polite");
    form.appendChild(status);

    cancelButton.addEventListener("click", (event) => {
      event.preventDefault();
      form.classList.add("hidden");
      setInlineCorrectionStatus(status, "");
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      handleManualCorrectionSubmit(item, form, status, saveButton);
    });

    return form;
  }

  function buildQuickFridgeControls(item, resolvedName, options = {}) {
    const { onFridgeSuccess } = options;
    const section = document.createElement("section");
    section.className = "item-quick-fridge";

    const title = document.createElement("h4");
    title.textContent = "冷蔵庫へ登録";
    section.appendChild(title);

    const selectLabel = document.createElement("label");
    selectLabel.textContent = "食材";
    const quickSelect = document.createElement("select");
    quickSelect.name = `quick_food_${item?.item_id ?? "unknown"}`;
    quickSelect.required = true;
    selectLabel.appendChild(quickSelect);
    section.appendChild(selectLabel);
    populateFoodSelectOptions(quickSelect, item?.food_id, resolvedName);
    quickSelect.disabled = !foodOptions.length;

    const quantityLabel = document.createElement("label");
    quantityLabel.textContent = "重量 (g)";
    const quantityInput = document.createElement("input");
    quantityInput.type = "number";
    quantityInput.min = "1";
    quantityInput.step = "1";
    quantityInput.placeholder = "例: 150";
    quantityLabel.appendChild(quantityInput);
    section.appendChild(quantityLabel);

    const expirationLabel = document.createElement("label");
    expirationLabel.textContent = "賞味期限";
    const expirationInput = document.createElement("input");
    expirationInput.type = "date";
    expirationLabel.appendChild(expirationInput);
    section.appendChild(expirationLabel);

    const actions = document.createElement("div");
    actions.className = "item-fridge-actions";
    const registerButton = document.createElement("button");
    registerButton.type = "button";
    registerButton.className = "secondary-btn";
    registerButton.textContent = "冷蔵庫へ登録";
    actions.appendChild(registerButton);
    section.appendChild(actions);

    const status = document.createElement("p");
    status.className = "item-fridge-status";
    status.setAttribute("aria-live", "polite");
    section.appendChild(status);

    registerButton.addEventListener("click", () =>
      handleAddIngredientToFridge({
        selectEl: quickSelect,
        quantityInput,
        expirationInput,
        statusTarget: status,
        triggerButton: registerButton,
        onSuccess: onFridgeSuccess,
      }),
    );

    if (!foodOptions.length) {
      const warningWrapper = document.createElement("div");
      warningWrapper.className = "food-options-warning";
      const warning = document.createElement("p");
      warning.className = "item-correction-status warn";
      let warnMsg = "利用可能な食材候補がありません。食材マスタを確認してください。";
      if (foodOptionsError) {
        if (typeof foodOptionsError === "string") {
          warnMsg = foodOptionsError;
        } else {
          try {
            warnMsg = JSON.stringify(foodOptionsError);
          } catch (e) {
            warnMsg = String(foodOptionsError);
          }
        }
      }
      warning.textContent = warnMsg;
      warningWrapper.appendChild(warning);

      const retryButton = document.createElement("button");
      retryButton.type = "button";
      retryButton.className = "ghost-btn";
      retryButton.textContent = "候補を再取得";
      retryButton.addEventListener("click", () =>
        handleFoodOptionReload({
          selectEl: quickSelect,
          warningEl: warning,
          defaultFoodId: item?.food_id,
          fallbackName: resolvedName,
          buttonEl: retryButton,
        }),
      );
      warningWrapper.appendChild(retryButton);
      section.appendChild(warningWrapper);
      registerButton.disabled = true;
    }

    return section;
  }

  async function handleManualCorrectionSubmit(item, form, statusTarget, submitButton) {
    if (!currentReceiptId) {
      setInlineCorrectionStatus(statusTarget, "レシートIDが不明です。", "error");
      return;
    }
    const itemId = item?.item_id;
    if (!itemId) {
      setInlineCorrectionStatus(statusTarget, "項目IDが不明です。", "error");
      return;
    }

    const rawInput = form.querySelector('[name="raw_text"]');
    const resolvedSelect = form.querySelector('select[name="resolved_food_name"]');
    const noteInput = form.querySelector('[name="note"]');

    const payload = {
      raw_text: rawInput?.value?.trim() ?? "",
      confidence: 0.95,
    };

    if (!payload.raw_text) {
      setInlineCorrectionStatus(statusTarget, "認識テキストを入力してください。", "error");
      rawInput?.focus();
      return;
    }

    if (!resolvedSelect || resolvedSelect.disabled) {
      setInlineCorrectionStatus(
        statusTarget,
        "食材候補が利用できないため保存できません。候補を再取得してください。",
        "error",
      );
      resolvedSelect?.focus();
      return;
    }

    const selectedOption = resolvedSelect.selectedOptions?.[0];
    if (!selectedOption || !selectedOption.value) {
      setInlineCorrectionStatus(statusTarget, "食材を選択してください。", "error");
      resolvedSelect.focus();
      return;
    }
    payload.food_id = Number(selectedOption.value);
    payload.resolved_food_name =
      selectedOption.dataset.foodName?.trim() || selectedOption.textContent?.trim() || "";

    if (noteInput?.value?.trim()) {
      payload.note = noteInput.value.trim();
    }
    submitButton.disabled = true;
    setInlineCorrectionStatus(statusTarget, "保存しています...", "info");

    try {
      const token = await ensureValidAccessToken();
      const response = await fetch(
        `${API_BASE_URL}/receipts/${currentReceiptId}/items/${itemId}/manual-resolution`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(payload),
        },
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        handleAuthError(response.status);
        throw new Error(data?.detail || "手動修正の保存に失敗しました。");
      }
      setInlineCorrectionStatus(statusTarget, "保存しました。", "success");
      form.classList.add("hidden");
      await loadReceiptDetails(currentReceiptId);
      setStatusMessage("手動修正を保存しました。", "success");
    } catch (error) {
      console.error(error);
      setInlineCorrectionStatus(
        statusTarget,
        error.message || "手動修正の保存に失敗しました。",
        "error",
      );
    } finally {
      submitButton.disabled = false;
    }
  }

  async function handleAddIngredientToFridge({
    selectEl,
    quantityInput,
    expirationInput,
    statusTarget,
    triggerButton,
    onSuccess,
  }) {
    if (!selectEl || selectEl.disabled) {
      setFridgeStatus(
        statusTarget,
        "食材候補が利用できません。候補を取得してから登録してください。",
        "error",
      );
      return;
    }

    const selectedOption = selectEl.selectedOptions?.[0];
    if (!selectedOption || !selectedOption.value) {
      setFridgeStatus(statusTarget, "登録する食材を選択してください。", "error");
      selectEl.focus();
      return;
    }

    if (!quantityInput) {
      setFridgeStatus(statusTarget, "重量入力欄が見つかりません。", "error");
      return;
    }

    const quantity = Number(quantityInput.value);
    if (Number.isNaN(quantity) || quantity <= 0) {
      setFridgeStatus(statusTarget, "1g以上の重量を入力してください。", "error");
      quantityInput.focus();
      return;
    }

    const payload = {
      food_id: Number(selectedOption.value),
      quantity_g: quantity,
    };

    if (expirationInput?.value) {
      const expirationValue = expirationInput.value;
      const expirationDate = new Date(expirationValue);
      if (Number.isNaN(expirationDate.getTime())) {
        setFridgeStatus(statusTarget, "賞味期限の日付が正しくありません。", "error");
        expirationInput.focus();
        return;
      }
      payload.expiration_date = expirationValue;
    }

    setFridgeStatus(statusTarget, "冷蔵庫に登録しています...", "info");
    triggerButton?.setAttribute("disabled", "true");

    try {
      const token = await ensureValidAccessToken();
      const response = await fetch(`${API_BASE_URL}/ingredients`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        handleAuthError(response.status);
        throw new Error(data?.detail || "冷蔵庫への登録に失敗しました。");
      }

      setFridgeStatus(statusTarget, "冷蔵庫へ登録しました。", "success");
      quantityInput.value = "";
      if (expirationInput) {
        expirationInput.value = "";
      }
      if (typeof onSuccess === "function") {
        onSuccess();
      }
    } catch (error) {
      console.error(error);
      setFridgeStatus(
        statusTarget,
        error.message || "冷蔵庫への登録に失敗しました。",
        "error",
      );
    } finally {
      triggerButton?.removeAttribute("disabled");
    }
  }

  function hideItemCard(card) {
    if (!card || card.classList.contains("item-card-hidden")) return;
    card.classList.add("item-card-hidden");
    setTimeout(() => {
      card.remove();
      if (itemsContainer && itemsContainer.children.length === 0) {
        itemsEmptyMessage?.classList.remove("hidden");
      }
    }, 220);
  }

  function markItemHidden(receiptId, itemId) {
    if (!receiptId || !itemId) return;
    const key = `rr.hidden_items.${receiptId}`;
    try {
      const raw = localStorage.getItem(key);
      const arr = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(arr)) return;
      if (!arr.includes(itemId)) {
        arr.push(itemId);
        localStorage.setItem(key, JSON.stringify(arr));
      }
      hiddenItemIds.add(itemId);
    } catch (e) {
      console.warn('failed to persist hidden items', e);
    }
  }

  function loadHiddenItemsForReceipt(receiptId) {
    const key = `rr.hidden_items.${receiptId}`;
    try {
      const raw = localStorage.getItem(key);
      const arr = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(arr) ? arr : []);
    } catch (e) {
      return new Set();
    }
  }

  function populateFoodSelectOptions(selectEl, selectedId, fallbackName) {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.disabled = true;
    placeholder.selected = !selectedId;
    placeholder.textContent = "食材を選択してください";
    selectEl.appendChild(placeholder);

    foodOptions.forEach((option) => {
      if (!option || typeof option.food_id === "undefined") return;
      const optionEl = document.createElement("option");
      optionEl.value = String(option.food_id);
      optionEl.textContent = option.food_name || `ID: ${option.food_id}`;
      optionEl.dataset.foodName = option.food_name || optionEl.textContent;
      if (
        selectedId &&
        String(option.food_id) === String(selectedId)
      ) {
        optionEl.selected = true;
      }
      selectEl.appendChild(optionEl);
    });

    if (selectedId && !selectEl.value) {
      const fallbackOption = document.createElement("option");
      fallbackOption.value = String(selectedId);
      fallbackOption.textContent = fallbackName || `ID: ${selectedId}`;
      fallbackOption.dataset.foodName = fallbackOption.textContent;
      fallbackOption.selected = true;
      selectEl.appendChild(fallbackOption);
    }
  }

  async function handleFoodOptionReload({
    selectEl,
    warningEl,
    defaultFoodId,
    fallbackName,
    buttonEl,
  }) {
    if (!selectEl || !warningEl) return;
    const previousValue = selectEl.value || defaultFoodId;
    const previousName =
      selectEl.selectedOptions?.[0]?.dataset.foodName || fallbackName || "";

    buttonEl?.setAttribute("disabled", "true");
    warningEl.className = "item-correction-status info";
    warningEl.textContent = "食材候補を再取得しています...";

    try {
      await ensureFoodOptions(true);
      populateFoodSelectOptions(selectEl, previousValue, previousName);
      selectEl.disabled = !foodOptions.length;
      if (foodOptions.length) {
        warningEl.className = "item-correction-status success";
        warningEl.textContent = "候補を再取得しました。食材を選択してください。";
        buttonEl?.remove();
      } else {
        warningEl.className = "item-correction-status warn";
        warningEl.textContent =
          "候補がまだ取得できません。時間を空けて再度お試しください。";
      }
    } catch (error) {
      console.error(error);
      warningEl.className = "item-correction-status error";
      warningEl.textContent =
        error.message || "候補の再取得に失敗しました。";
    } finally {
      buttonEl?.removeAttribute("disabled");
    }
  }

  function setInlineCorrectionStatus(target, text, type = "info") {
    if (!target) return;
    target.textContent = text;
    target.className = `item-correction-status ${type}`;
  }

  function setFridgeStatus(target, text, type = "info") {
    if (!target) return;
    target.textContent = text;
    target.className = `item-fridge-status ${type}`;
  }

  function resetResults() {
    textOutput.textContent = "";
    toggleElement(textSection, false);
    updateDownloadLink(null, false);
    if (linesContainer) {
      linesContainer.innerHTML = "";
    }
    linesEmptyMessage?.classList.remove("hidden");
    if (itemsContainer) {
      itemsContainer.innerHTML = "";
    }
    itemsEmptyMessage?.classList.remove("hidden");
    toggleElement(itemsSection, false);
  }

  function initializeState() {
    setStatusBadge("idle");
    setStatusMessage("まだ処理は開始されていません。", "info");
    toggleElement(textSection, false);
    toggleElement(receiptMeta, false);
    toggleElement(itemsSection, false);
    toggleRefreshButton();
  }

  function toggleRefreshButton() {
    if (!refreshStatusBtn) return;
    refreshStatusBtn.disabled = !currentReceiptId;
  }

  function setupSectionToggleButtons() {
    const buttons = document.querySelectorAll(".section-toggle-btn");
    buttons.forEach((button) => {
      const section = button.closest(".section-collapsible");
      if (!section) return;
      const targetId = button.getAttribute("aria-controls");
      const target = targetId ? document.getElementById(targetId) : null;
      const updateState = (isCollapsed) => {
        button.textContent = isCollapsed ? "表示" : "非表示";
        button.setAttribute("aria-expanded", String(!isCollapsed));
        if (target) {
          target.setAttribute("aria-hidden", String(isCollapsed));
        }
      };
      button.addEventListener("click", () => {
        const isCollapsed = section.classList.toggle("section-collapsed");
        updateState(isCollapsed);
      });
      updateState(section.classList.contains("section-collapsed"));
    });
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
    // Coerce objects to readable text
    let out = text;
    if (typeof text === "object" && text !== null) {
      if (typeof text.message === "string" && text.message.trim()) {
        out = text.message;
      } else {
        try {
          out = JSON.stringify(text);
        } catch (e) {
          out = String(text);
        }
      }
    }
    statusMessage.textContent = String(out);
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

  function formatYesNo(value) {
    if (typeof value === "undefined" || value === null) {
      return "-";
    }
    return value ? "はい" : "いいえ";
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
