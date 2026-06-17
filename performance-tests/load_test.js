import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 100,
  duration: "1m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000", "p(99)<2000"]
  }
};

const BASE_URL = __ENV.BASE_URL || "http://localhost";
const TENANT_EMAIL = __ENV.TENANT_EMAIL || "";
const TENANT_PASSWORD = __ENV.TENANT_PASSWORD || "";
const ROOM_ID = __ENV.ROOM_ID || "";

function login() {
  const res = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: TENANT_EMAIL, password: TENANT_PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(res, { "login 200": (r) => r.status === 200 });
  const body = res.json();
  return body?.token?.access_token;
}

let token = null;

export default function () {
  if (!ROOM_ID) {
    sleep(1);
    return;
  }

  if (!token) {
    token = login();
    if (!token) {
      sleep(1);
      return;
    }
  }

  const payload = {
    room_id: ROOM_ID,
    scheduled_time: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    note: "k6 load test"
  };

  const res = http.post(
    `${BASE_URL}/api/v1/appointments/`,
    JSON.stringify(payload),
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      }
    }
  );

  check(res, { "create appointment 201": (r) => r.status === 201 });
  sleep(0.2);
}
