import { sleep } from "k6";

import { DEFAULT_THRESHOLDS } from "../utils/config.js";
import { browseRoomsJourney } from "../scenarios/browse.js";
import { searchJourney } from "../scenarios/search.js";
import { loginRole } from "../utils/auth.js";
import { randomPauseRange } from "../utils/random.js";
import { setupSuite } from "../utils/setup.js";

export const options = {
  scenarios: {
    browse_rooms: {
      executor: "constant-vus",
      exec: "browseRoomsFlow",
      vus: Number(__ENV.LOAD_BROWSE_VUS || 70),
      duration: __ENV.LOAD_DURATION || "10m",
      gracefulStop: "15s",
    },
    search_rooms: {
      executor: "constant-vus",
      exec: "searchFlow",
      vus: Number(__ENV.LOAD_SEARCH_VUS || 20),
      duration: __ENV.LOAD_DURATION || "10m",
      gracefulStop: "15s",
    },
    auth_logins: {
      executor: "constant-vus",
      exec: "authFlow",
      vus: Number(__ENV.LOAD_AUTH_VUS || 10),
      duration: __ENV.LOAD_DURATION || "10m",
      gracefulStop: "15s",
    },
  },
  thresholds: DEFAULT_THRESHOLDS,
};

export function setup() {
  return setupSuite();
}

export function browseRoomsFlow(setupData) {
  browseRoomsJourney(setupData);
}

export function searchFlow() {
  searchJourney();
}

export function authFlow() {
  const role = Math.random() < 0.75 ? "tenant" : "landlord";
  loginRole(role, { force: true, pauseAfter: true });
  sleep(randomPauseRange(0.5, 1.5));
}
