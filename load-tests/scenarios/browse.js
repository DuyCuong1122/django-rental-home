import { sleep } from "k6";

import { DEFAULT_LIMIT, HEALTH_PATH } from "../utils/config.js";
import { pickRoomId, FIXTURES } from "../utils/data.js";
import { get } from "../utils/http.js";
import { chance, pickRandom, pickWeighted, randomInt, randomPauseRange } from "../utils/random.js";

function randomBrowseQuery() {
  const area = pickRandom(FIXTURES.browseAreas, FIXTURES.browseAreas[0]);
  return {
    province: area.province,
    district: area.district,
    limit: randomInt(10, DEFAULT_LIMIT),
    offset: randomInt(0, 2) * 10,
  };
}

function randomNearbyQuery() {
  const location = pickRandom(FIXTURES.nearbyLocations, FIXTURES.nearbyLocations[0]);
  return {
    latitude: location.latitude,
    longitude: location.longitude,
    radius_km: location.radius_km,
    limit: randomInt(10, DEFAULT_LIMIT),
    offset: 0,
  };
}

export function healthJourney() {
  get(HEALTH_PATH, {
    endpoint: "health.check",
    category: "public",
    expectedStatuses: [200],
  });
}

export function recentRoomsJourney() {
  get("/rooms/recent", {
    endpoint: "rooms.recent",
    category: "heavy",
    expectedStatuses: [200],
    query: randomBrowseQuery(),
  });
}

export function recommendedRoomsJourney() {
  get("/rooms/recommended", {
    endpoint: "rooms.recommended",
    category: "heavy",
    expectedStatuses: [200],
    query: randomBrowseQuery(),
  });
}

export function nearbyRoomsJourney() {
  get("/rooms/nearby", {
    endpoint: "rooms.nearby",
    category: "heavy",
    expectedStatuses: [200],
    query: randomNearbyQuery(),
  });
}

export function roomDetailJourney(setupData = {}) {
  const roomId = pickRoomId(setupData);
  if (!roomId) {
    return;
  }

  get(`/rooms/${roomId}`, {
    endpoint: "rooms.detail",
    category: "heavy",
    expectedStatuses: [200, 404],
  });
}

export function browseRoomsJourney(setupData = {}) {
  const journey = pickWeighted([
    { weight: 0.05, value: "health" },
    { weight: 0.30, value: "recent" },
    { weight: 0.25, value: "recommended" },
    { weight: 0.15, value: "nearby" },
    { weight: 0.25, value: "detail" },
  ]);

  if (journey === "health") {
    healthJourney();
  } else if (journey === "recent") {
    recentRoomsJourney();
  } else if (journey === "recommended") {
    recommendedRoomsJourney();
  } else if (journey === "nearby") {
    nearbyRoomsJourney();
  } else {
    roomDetailJourney(setupData);
  }

  if (chance(0.35)) {
    roomDetailJourney(setupData);
  }

  sleep(randomPauseRange(0.4, 1.6));
}
