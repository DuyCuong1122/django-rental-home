import { SharedArray } from "k6/data";

import { CHAT_ROOM_IDS, ROOM_IDS } from "./config.js";
import { pickRandom, unique } from "./random.js";

const fixtureHolder = new SharedArray("load-test-fixtures", () => [
  JSON.parse(open("../data/search-fixtures.json")),
]);

export const FIXTURES = fixtureHolder[0];

export function extractRoomIds(payload) {
  if (!Array.isArray(payload)) {
    return [];
  }

  return payload
    .map((item) => item?.id)
    .filter(Boolean)
    .map((id) => String(id));
}

export function extractChatRoomIds(payload) {
  const rooms = payload?.data || [];
  if (!Array.isArray(rooms)) {
    return [];
  }

  return rooms
    .map((item) => item?.id)
    .filter(Boolean)
    .map((id) => String(id));
}

export function extractMessageIds(payload) {
  const messages = payload?.data || [];
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages
    .map((item) => item?.id)
    .filter(Boolean)
    .map((id) => String(id));
}

export function pickRoomId(setupData = {}) {
  const roomIds = unique([...(setupData.roomIds || []), ...ROOM_IDS]);
  return pickRandom(roomIds);
}

export function pickChatRoomId(setupData = {}, discoveredChatRoomIds = []) {
  const chatRoomIds = unique([
    ...(setupData.chatRoomIds || []),
    ...discoveredChatRoomIds,
    ...CHAT_ROOM_IDS,
  ]);
  return pickRandom(chatRoomIds);
}
