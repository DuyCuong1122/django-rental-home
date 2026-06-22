import { browseRoomsJourney } from "../scenarios/browse.js";
import { searchJourney } from "../scenarios/search.js";
import { chatJourney } from "../scenarios/chat.js";
import { appointmentJourney } from "../scenarios/appointment.js";
import { DEFAULT_THRESHOLDS } from "../utils/config.js";
import { pickWeighted } from "../utils/random.js";
import { setupSuite } from "../utils/setup.js";

export const options = {
  scenarios: {
    soak_mix: {
      executor: "constant-vus",
      exec: "soakFlow",
      vus: Number(__ENV.SOAK_VUS || 50),
      duration: __ENV.SOAK_DURATION || "4h",
      gracefulStop: "30s",
    },
  },
  thresholds: DEFAULT_THRESHOLDS,
};

export function setup() {
  return setupSuite();
}

export function soakFlow(setupData) {
  const journey = pickWeighted([
    { weight: 0.55, value: "browse" },
    { weight: 0.25, value: "search" },
    { weight: 0.15, value: "chat" },
    { weight: 0.05, value: "appointment" },
  ]);

  if (journey === "browse") {
    browseRoomsJourney(setupData);
  } else if (journey === "search") {
    searchJourney();
  } else if (journey === "chat") {
    chatJourney(setupData);
  } else {
    appointmentJourney(setupData);
  }
}
