import { sleep } from "k6";

import { DEFAULT_THRESHOLDS } from "../utils/config.js";
import { browseRoomsJourney, healthJourney, roomDetailJourney } from "../scenarios/browse.js";
import { searchJourney } from "../scenarios/search.js";
import { setupSuite } from "../utils/setup.js";

export const options = {
  vus: Number(__ENV.SMOKE_VUS || 3),
  duration: __ENV.SMOKE_DURATION || "1m",
  thresholds: DEFAULT_THRESHOLDS,
};

export function setup() {
  return setupSuite();
}

export default function (setupData) {
  healthJourney();
  browseRoomsJourney(setupData);
  roomDetailJourney(setupData);
  searchJourney();
  sleep(1);
}
