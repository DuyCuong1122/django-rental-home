import { sleep } from "k6";

import { ACCESS_TOKEN_TTL_SECONDS, credentialsFor, hasCredentials } from "./config.js";
import { authSuccessRate } from "./metrics.js";
import { postJson, safeJson } from "./http.js";
import { randomPauseRange } from "./random.js";

const tokenCache = {};

function cacheSession(role, session) {
  if (!session?.accessToken) {
    return null;
  }

  tokenCache[role] = {
    ...session,
    expiresAt: Date.now() + ACCESS_TOKEN_TTL_SECONDS * 1000,
  };

  return tokenCache[role];
}

function readCachedSession(role) {
  const session = tokenCache[role];
  if (!session) {
    return null;
  }

  if (session.expiresAt <= Date.now() + 30 * 1000) {
    return null;
  }

  return session;
}

export function loginRole(role = "tenant", options = {}) {
  const { force = false, pauseAfter = false } = options;

  if (!force) {
    const cached = readCachedSession(role);
    if (cached) {
      return cached;
    }
  }

  if (!hasCredentials(role)) {
    authSuccessRate.add(false, { role });
    return null;
  }

  const credentials = credentialsFor(role);
  const response = postJson(
    "/auth/login",
    {
      email: credentials.email,
      password: credentials.password,
    },
    {
      endpoint: "auth.login",
      category: "authenticated",
      expectedStatuses: [200],
      tags: {
        role,
      },
    }
  );

  const payload = safeJson(response);
  const accessToken = payload?.token?.access_token;
  const refreshToken = payload?.token?.refresh_token;
  const userId = payload?.user?.id;
  const success = Boolean(accessToken);

  authSuccessRate.add(success, { role });

  if (!success) {
    return null;
  }

  const session = cacheSession(role, {
    accessToken,
    refreshToken,
    userId,
  });

  if (pauseAfter) {
    sleep(randomPauseRange(0.1, 0.4));
  }

  return session;
}

export function getAccessToken(role = "tenant") {
  const session = loginRole(role, { force: false });
  return session?.accessToken || null;
}

export function bearerHeaders(token) {
  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}
