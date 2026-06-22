import { sleep } from "k6";

import { SEARCH_LIMIT } from "../utils/config.js";
import { FIXTURES } from "../utils/data.js";
import { get } from "../utils/http.js";
import { chance, pickRandom, randomInt, randomPauseRange } from "../utils/random.js";

export function buildSearchQuery() {
  const area = pickRandom(FIXTURES.searchAreas, FIXTURES.searchAreas[0]);
  const priceRange = pickRandom(FIXTURES.priceRanges, FIXTURES.priceRanges[0]);
  const areaRange = pickRandom(FIXTURES.areaRanges, FIXTURES.areaRanges[0]);
  const keyword = chance(0.75) ? pickRandom(FIXTURES.keywords, FIXTURES.keywords[0]) : "";

  return {
    keyword,
    district: area.district,
    ward: chance(0.8) ? area.ward : "",
    min_price: priceRange.min,
    max_price: priceRange.max,
    min_area: areaRange.min,
    max_area: areaRange.max,
    limit: randomInt(10, SEARCH_LIMIT),
    offset: randomInt(0, 3) * 10,
  };
}

export function searchJourney() {
  get("/search/rooms", {
    endpoint: "search.rooms",
    category: "heavy",
    expectedStatuses: [200],
    query: buildSearchQuery(),
  });

  sleep(randomPauseRange(0.5, 1.8));
}
