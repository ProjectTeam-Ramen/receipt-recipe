(function () {
  const API_PATH = "/api/v1";
  const LOCAL_STORAGE_KEY = "rr.api_base_url";

  function readOverride() {
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  function deriveDefaultBaseUrl() {
    const override = readOverride();
    if (override) return override;

    const { protocol, hostname } = window.location;
    const localHosts = new Set(["localhost", "127.0.0.1"]);
    const targetPort = "8000";

    // 1. 開発環境 (localhost または 127.0.0.1) の場合
    // フロントエンドとは別にバックエンドがポート8000で動いていると想定して直接指定します
    if (localHosts.has(hostname)) {
      return `${protocol}//${hostname}:${targetPort}${API_PATH}`;
    }

    // 2. 本番環境 (VPSのIPアドレス、またはドメイン) の場合
    // Nginxが "/api/v1" へのリクエストを内部で8000番に転送するため、
    // ブラウザからはポート番号を指定せず、相対パスでアクセスさせます。
    return API_PATH;
  }

  window.APP_CONFIG = window.APP_CONFIG || {};
  if (!window.APP_CONFIG.apiBaseUrl) {
    window.APP_CONFIG.apiBaseUrl = deriveDefaultBaseUrl();
  }

  const defaultStorageKeys = {
    accessToken: "rr.access_token",
    refreshToken: "rr.refresh_token",
    accessTokenExpiresAt: "rr.access_token_expires_at",
    userName: "rr.user_name",
    userEmail: "rr.user_email",
  };

  window.APP_CONFIG.storageKeys = Object.assign(
    {},
    defaultStorageKeys,
    window.APP_CONFIG.storageKeys || {}
  );
})();