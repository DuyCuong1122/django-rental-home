import { browseRoomsJourney } from "../scenarios/browse.js";
import { searchJourney } from "../scenarios/search.js";
import { chatJourney } from "../scenarios/chat.js";
import { appointmentJourney } from "../scenarios/appointment.js";
import { loginRole } from "../utils/auth.js";
import { STRESS_THRESHOLDS } from "../utils/config.js";
import { pickWeighted } from "../utils/random.js";
import { setupSuite } from "../utils/setup.js";

export const options = {
  scenarios: {
    stress_mix: {
      executor: "ramping-vus",
      exec: "stressFlow",
      startVUs: 0,
      stages: [
        { duration: "2m", target: 20 },
        { duration: "2m", target: 50 },
        { duration: "2m", target: 100 },
        { duration: "2m", target: 200 },
        { duration: "2m", target: 500 },
        { duration: "2m", target: 0 },
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds: STRESS_THRESHOLDS,
};

export function setup() {
  return setupSuite();
}

export function stressFlow(setupData) {
  const journey = pickWeighted([
    { weight: 0.45, value: "browse" },
    { weight: 0.20, value: "search" },
    { weight: 0.15, value: "chat" },
    { weight: 0.15, value: "auth" },
    { weight: 0.05, value: "appointment" },
  ]);

  if (journey === "browse") {
    browseRoomsJourney(setupData);
  } else if (journey === "search") {
    searchJourney();
  } else if (journey === "chat") {
    chatJourney(setupData);
  } else if (journey === "appointment") {
    appointmentJourney(setupData);
  } else {
    const role = Math.random() < 0.75 ? "tenant" : "landlord";
    loginRole(role, { force: true, pauseAfter: true });
  }
}
