import http from "k6/http";
import { check } from "k6";

import { API_PREFIX, BASE_URL } from "./config.js";
import { recordHttpMetrics } from "./metrics.js";

function normalizePath(path) {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (normalized.startsWith(API_PREFIX)) {
    return `${BASE_URL}${normalized}`;
  }

  return `${BASE_URL}${API_PREFIX}${normalized}`;
}

export function toQueryString(query = {}) {
  return Object.entries(query)
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join("&");
}

export function buildUrl(path, query) {
  const url = normalizePath(path);
  const queryString = toQueryString(query);
  return queryString ? `${url}?${queryString}` : url;
}

export function safeJson(response) {
  try {
    return response.json();
  } catch (_error) {
    return null;
  }
}

function runCheck(endpoint, response, expectedStatuses) {
  return check(response, {
    [`${endpoint} status ok`]: (res) => expectedStatuses.includes(res.status),
  });
}

export function get(path, options = {}) {
  const {
    query,
    headers = {},
    expectedStatuses = [200],
    endpoint = path,
    category = "public",
    tags = {},
  } = options;

  const url = buildUrl(path, query);
  const response = http.get(url, {
    headers,
    tags: {
      endpoint,
      category,
      ...tags,
    },
  });
  const passed = runCheck(endpoint, response, expectedStatuses);
  recordHttpMetrics(endpoint, category, response, passed);
  return response;
}

export function postJson(path, payload = {}, options = {}) {
  const {
    query,
    headers = {},
    expectedStatuses = [200],
    endpoint = path,
    category = "authenticated",
    tags = {},
  } = options;

  const url = buildUrl(path, query);
  const response = http.post(url, JSON.stringify(payload), {
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    tags: {
      endpoint,
      category,
      ...tags,
    },
  });
  const passed = runCheck(endpoint, response, expectedStatuses);
  recordHttpMetrics(endpoint, category, response, passed);
  return response;
}
