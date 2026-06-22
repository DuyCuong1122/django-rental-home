import { Counter, Rate, Trend } from "k6/metrics";

export const apiPublicDuration = new Trend("api_public_duration", true);
export const apiAuthenticatedDuration = new Trend("api_authenticated_duration", true);
export const apiHeavyDuration = new Trend("api_heavy_duration", true);
export const apiStatusTotal = new Counter("api_status_total");
export const apiScenarioErrors = new Rate("api_scenario_errors");
export const authSuccessRate = new Rate("auth_success_rate");

const HEAVY_ENDPOINTS = new Set([
  "rooms.recent",
  "rooms.recommended",
  "rooms.nearby",
  "rooms.detail",
  "search.rooms",
  "chat.inbox",
  "chat.room_detail",
  "chat.messages",
  "chat.mark_read",
  "appointments.create",
]);

export function recordHttpMetrics(endpoint, category, response, passed) {
  const tags = {
    endpoint,
    category,
    status: String(response.status),
  };

  apiStatusTotal.add(1, tags);
  apiScenarioErrors.add(!passed, tags);

  if (typeof response.timings?.duration === "number") {
    if (category === "authenticated") {
      apiAuthenticatedDuration.add(response.timings.duration, tags);
    } else {
      apiPublicDuration.add(response.timings.duration, tags);
    }

    if (category === "heavy" || HEAVY_ENDPOINTS.has(endpoint)) {
      apiHeavyDuration.add(response.timings.duration, tags);
    }
  }
}
