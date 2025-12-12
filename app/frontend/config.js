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

  function deriveGithubDevHost(hostname, targetPort) {
    if (!hostname.endsWith(".github.dev")) return null;
    const replaced = hostname.replace(/-(\d+)(\.(?:preview\.)?app\.github\.dev)$/i, `-${targetPort}$2`);
    return replaced !== hostname ? replaced : null;
  }

  function deriveDefaultBaseUrl() {
    const override = readOverride();
    if (override) return override;

    const { protocol, hostname, host } = window.location;
    const localHosts = new Set(["localhost", "127.0.0.1"]);
    const targetPort = "8000";

    if (localHosts.has(hostname)) {
      return `${protocol}//${hostname}:${targetPort}${API_PATH}`;
    }

    if (host && host.includes(":")) {
      const hostWithoutPort = host.split(":")[0];
      return `${protocol}//${hostWithoutPort}:${targetPort}${API_PATH}`;
    }

    const githubHost = deriveGithubDevHost(hostname, targetPort);
    if (githubHost) {
      return `${protocol}//${githubHost}${API_PATH}`;
    }

    // Fallback to relative path when the backend host cannot be derived
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

  if (typeof document !== "undefined" && document.head) {
    const existingIcon = document.querySelector("link[rel='icon']");
    if (!existingIcon) {
      const iconLink = document.createElement("link");
      iconLink.rel = "icon";
      iconLink.type = "image/svg+xml";
      iconLink.href = "favicon.svg";
      document.head.appendChild(iconLink);
    }
  }
})();
