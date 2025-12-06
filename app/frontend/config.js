(function () {
  const isLocalhost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const defaultBaseUrl = isLocalhost
    ? "http://127.0.0.1:8000/api/v1"
    : "/api/v1";

  window.APP_CONFIG = window.APP_CONFIG || {};
  if (!window.APP_CONFIG.apiBaseUrl) {
    window.APP_CONFIG.apiBaseUrl = defaultBaseUrl;
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
