import { sleep } from "k6";

import { ENABLE_WRITE_SCENARIOS } from "../utils/config.js";
import { getAccessToken } from "../utils/auth.js";
import { pickRoomId } from "../utils/data.js";
import { postJson } from "../utils/http.js";
import { randomInt, randomPauseRange } from "../utils/random.js";

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export function appointmentJourney(setupData = {}) {
  if (!ENABLE_WRITE_SCENARIOS) {
    sleep(randomPauseRange(0.5, 1.0));
    return;
  }

  const token = getAccessToken("tenant");
  const roomId = pickRoomId(setupData);
  if (!token || !roomId) {
    sleep(randomPauseRange(0.5, 1.0));
    return;
  }

  const scheduledAt = new Date(Date.now() + randomInt(4, 72) * 60 * 60 * 1000).toISOString();

  postJson(
    "/appointments/",
    {
      room_id: roomId,
      scheduled_time: scheduledAt,
      note: "k6 appointment flow",
    },
    {
      endpoint: "appointments.create",
      category: "heavy",
      expectedStatuses: [201],
      headers: authHeaders(token),
    }
  );

  sleep(randomPauseRange(0.8, 2.0));
}
