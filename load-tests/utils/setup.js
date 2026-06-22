import { CHAT_LIMIT, DEFAULT_LIMIT, SEARCH_LIMIT } from "./config.js";
import { loginRole } from "./auth.js";
import { extractChatRoomIds, extractMessageIds, extractRoomIds, FIXTURES } from "./data.js";
import { get, safeJson } from "./http.js";
import { unique } from "./random.js";

export function setupSuite() {
  const roomIds = [];
  const chatRoomIds = [];
  const messageIdsByRoom = {};

  const browseArea = FIXTURES.browseAreas[0];
  const searchArea = FIXTURES.searchAreas[0];
  const priceRange = FIXTURES.priceRanges[0];
  const areaRange = FIXTURES.areaRanges[0];
  const nearbyLocation = FIXTURES.nearbyLocations[0];

  const recentResponse = get("/rooms/recent", {
    endpoint: "setup.rooms_recent",
    category: "public",
    expectedStatuses: [200],
    query: {
      province: browseArea.province,
      district: browseArea.district,
      limit: DEFAULT_LIMIT,
      offset: 0,
    },
  });
  roomIds.push(...extractRoomIds(safeJson(recentResponse)));

  const recommendedResponse = get("/rooms/recommended", {
    endpoint: "setup.rooms_recommended",
    category: "public",
    expectedStatuses: [200],
    query: {
      province: browseArea.province,
      district: browseArea.district,
      limit: DEFAULT_LIMIT,
      offset: 0,
    },
  });
  roomIds.push(...extractRoomIds(safeJson(recommendedResponse)));

  const searchResponse = get("/search/rooms", {
    endpoint: "setup.search_rooms",
    category: "heavy",
    expectedStatuses: [200],
    query: {
      keyword: FIXTURES.keywords[0],
      district: searchArea.district,
      ward: searchArea.ward,
      min_price: priceRange.min,
      max_price: priceRange.max,
      min_area: areaRange.min,
      max_area: areaRange.max,
      limit: SEARCH_LIMIT,
      offset: 0,
    },
  });
  roomIds.push(...extractRoomIds(safeJson(searchResponse)));

  const nearbyResponse = get("/rooms/nearby", {
    endpoint: "setup.rooms_nearby",
    category: "heavy",
    expectedStatuses: [200],
    query: {
      latitude: nearbyLocation.latitude,
      longitude: nearbyLocation.longitude,
      radius_km: nearbyLocation.radius_km,
      limit: DEFAULT_LIMIT,
      offset: 0,
    },
  });
  roomIds.push(...extractRoomIds(safeJson(nearbyResponse)));

  const tenantSession = loginRole("tenant");
  if (tenantSession?.accessToken) {
    const inboxResponse = get("/chat/rooms", {
      endpoint: "setup.chat_inbox",
      category: "heavy",
      expectedStatuses: [200],
      headers: {
        Authorization: `Bearer ${tenantSession.accessToken}`,
      },
      query: {
        limit: CHAT_LIMIT,
        filter: "all",
      },
    });
    const inboxPayload = safeJson(inboxResponse);
    const discoveredChatRoomIds = extractChatRoomIds(inboxPayload);
    chatRoomIds.push(...discoveredChatRoomIds);

    if (discoveredChatRoomIds.length > 0) {
      const chatRoomId = discoveredChatRoomIds[0];
      const messageResponse = get(`/chat/rooms/${chatRoomId}/messages`, {
        endpoint: "setup.chat_messages",
        category: "heavy",
        expectedStatuses: [200],
        headers: {
          Authorization: `Bearer ${tenantSession.accessToken}`,
        },
        query: {
          limit: CHAT_LIMIT,
        },
      });
      messageIdsByRoom[chatRoomId] = extractMessageIds(safeJson(messageResponse));
    }
  }

  return {
    roomIds: unique(roomIds),
    chatRoomIds: unique(chatRoomIds),
    messageIdsByRoom,
  };
}
