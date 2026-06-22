function splitCsv(rawValue) {
  return (rawValue || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function parseBoolean(rawValue, defaultValue = false) {
  if (rawValue === undefined || rawValue === null || rawValue === "") {
    return defaultValue;
  }

  return ["1", "true", "yes", "on"].includes(String(rawValue).toLowerCase());
}

export const BASE_URL = (__ENV.BASE_URL || "http://localhost").replace(/\/$/, "");
export const API_PREFIX = (__ENV.API_PREFIX || "/api/v1").replace(/\/$/, "");
export const HEALTH_PATH = __ENV.HEALTH_PATH || `${API_PREFIX}/health`;

export const TENANT_EMAIL = __ENV.TENANT_EMAIL || "tenant@example.com";
export const TENANT_PASSWORD = __ENV.TENANT_PASSWORD || "Password123!";
export const LANDLORD_EMAIL = __ENV.LANDLORD_EMAIL || "landlord@example.com";
export const LANDLORD_PASSWORD = __ENV.LANDLORD_PASSWORD || "Password123!";
export const ACCESS_TOKEN_TTL_SECONDS = Number(__ENV.ACCESS_TOKEN_TTL_SECONDS || 900);

export const ROOM_IDS = splitCsv(__ENV.ROOM_IDS || __ENV.ROOM_ID || "");
export const CHAT_ROOM_IDS = splitCsv(__ENV.CHAT_ROOM_IDS || "");

export const DEFAULT_LIMIT = Number(__ENV.DEFAULT_LIMIT || 20);
export const SEARCH_LIMIT = Number(__ENV.SEARCH_LIMIT || 20);
export const CHAT_LIMIT = Number(__ENV.CHAT_LIMIT || 20);

export const ENABLE_CHAT_SCENARIO = parseBoolean(__ENV.ENABLE_CHAT_SCENARIO, true);
export const ENABLE_WRITE_SCENARIOS = parseBoolean(__ENV.ENABLE_WRITE_SCENARIOS, false);

export const DEFAULT_THRESHOLDS = {
  http_req_failed: ["rate<0.01"],
  http_req_duration: ["p(95)<500", "p(99)<1000"],
  checks: ["rate>0.99"],
};

export const STRESS_THRESHOLDS = {
  http_req_failed: ["rate<0.05"],
  http_req_duration: ["p(95)<1200", "p(99)<2500"],
  checks: ["rate>0.95"],
};

export function credentialsFor(role = "tenant") {
  if (role === "landlord") {
    return {
      role,
      email: LANDLORD_EMAIL,
      password: LANDLORD_PASSWORD,
    };
  }

  return {
    role: "tenant",
    email: TENANT_EMAIL,
    password: TENANT_PASSWORD,
  };
}

export function hasCredentials(role = "tenant") {
  const credentials = credentialsFor(role);
  return Boolean(credentials.email && credentials.password);
}
