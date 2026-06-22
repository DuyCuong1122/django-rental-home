import { sleep } from "k6";

import { CHAT_LIMIT, ENABLE_CHAT_SCENARIO } from "../utils/config.js";
import { getAccessToken } from "../utils/auth.js";
import { pickChatRoomId, extractChatRoomIds, extractMessageIds } from "../utils/data.js";
import { get, postJson, safeJson } from "../utils/http.js";
import { chance, randomInt, randomPauseRange } from "../utils/random.js";

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export function chatJourney(setupData = {}) {
  if (!ENABLE_CHAT_SCENARIO) {
    sleep(randomPauseRange(0.5, 1.0));
    return;
  }

  const token = getAccessToken("tenant");
  if (!token) {
    sleep(randomPauseRange(0.5, 1.0));
    return;
  }

  const inboxResponse = get("/chat/rooms", {
    endpoint: "chat.inbox",
    category: "heavy",
    expectedStatuses: [200],
    headers: authHeaders(token),
    query: {
      limit: randomInt(10, CHAT_LIMIT),
      filter: chance(0.25) ? "unread" : "all",
    },
  });
  const inboxPayload = safeJson(inboxResponse);
  const discoveredChatRoomIds = extractChatRoomIds(inboxPayload);
  const chatRoomId = pickChatRoomId(setupData, discoveredChatRoomIds);

  if (!chatRoomId) {
    sleep(randomPauseRange(0.4, 1.2));
    return;
  }

  get(`/chat/rooms/${chatRoomId}`, {
    endpoint: "chat.room_detail",
    category: "heavy",
    expectedStatuses: [200],
    headers: authHeaders(token),
  });

  const messagesResponse = get(`/chat/rooms/${chatRoomId}/messages`, {
    endpoint: "chat.messages",
    category: "heavy",
    expectedStatuses: [200],
    headers: authHeaders(token),
    query: {
      limit: randomInt(10, CHAT_LIMIT),
    },
  });
  const messagesPayload = safeJson(messagesResponse);
  const messageIds = extractMessageIds(messagesPayload);
  const markReadCandidate = messageIds[0] || setupData.messageIdsByRoom?.[chatRoomId]?.[0];

  if (markReadCandidate && chance(0.35)) {
    postJson(
      `/chat/rooms/${chatRoomId}/read`,
      {
        message_id: markReadCandidate,
      },
      {
        endpoint: "chat.mark_read",
        category: "heavy",
        expectedStatuses: [200],
        headers: authHeaders(token),
      }
    );
  }

  if (chance(0.3)) {
    get("/chat/unread-count", {
      endpoint: "chat.unread_count",
      category: "authenticated",
      expectedStatuses: [200],
      headers: authHeaders(token),
    });
  }

  sleep(randomPauseRange(0.5, 1.5));
}
