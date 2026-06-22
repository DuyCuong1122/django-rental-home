# Rental House Platform k6 Load Test Suite

This suite is built from the current Postman collection at `postman/RentalHousePlatform.postman_collection.json`.

## API Classification

### Public APIs

- `GET /api/v1/health`
- `GET /api/v1/rooms/recent`
- `GET /api/v1/rooms/recommended`
- `GET /api/v1/rooms/nearby`
- `GET /api/v1/rooms/{room_id}`
- `GET /api/v1/search/rooms`

### Authenticated APIs

- `POST /api/v1/auth/login`
- `GET /api/v1/profile/me`
- `POST /api/v1/appointments/`
- `GET /api/v1/chat/rooms`
- `GET /api/v1/chat/rooms/{chat_room_id}`
- `GET /api/v1/chat/rooms/{chat_room_id}/messages`
- `POST /api/v1/chat/rooms/{chat_room_id}/read`
- `GET /api/v1/chat/unread-count`
- `POST /api/v1/upload/presigned-url`

### Heavy APIs

- `GET /api/v1/search/rooms`
- `GET /api/v1/rooms/recent`
- `GET /api/v1/rooms/recommended`
- `GET /api/v1/rooms/nearby`
- `GET /api/v1/chat/rooms`
- `GET /api/v1/chat/rooms/{chat_room_id}/messages`
- `POST /api/v1/appointments/`

## Directory Layout

```text
load-tests/
├── smoke/
├── load/
├── stress/
├── soak/
├── scenarios/
├── data/
└── utils/
```

## Test Modes

### Smoke

- File: `load-tests/smoke/smoke.js`
- Goal: fast liveliness check for `health`, room browse, room detail, and search
- Default: `3` VUs for `1m`

### Load

- File: `load-tests/load/load.js`
- Goal: normal production traffic simulation with 100 concurrent users
- Mix:
  - `70%` browse rooms
  - `20%` search rooms
  - `10%` authentication load

### Stress

- File: `load-tests/stress/stress.js`
- Goal: find the break point
- Ramp: `20 -> 50 -> 100 -> 200 -> 500` VUs

### Soak

- File: `load-tests/soak/soak.js`
- Goal: catch memory leak, connection leak, and pool exhaustion
- Default: `50` VUs for `4h`

## Token Reuse Strategy

- `load-tests/utils/auth.js` caches access tokens per VU.
- Chat and authenticated read scenarios reuse tokens instead of logging in on every request.
- The dedicated auth scenario in `load/load.js` forces fresh login requests to measure auth throughput separately.

## Randomization Strategy

- Search terms come from `load-tests/data/search-fixtures.json`.
- Browse traffic rotates `recent`, `recommended`, `nearby`, and room detail flows.
- Search traffic randomizes `district`, `ward`, `keyword`, `price range`, `area range`, `limit`, and `offset`.
- Suite bootstraps room IDs and chat room IDs in `setup()` to avoid pinning to a single hard-coded record.

## Production-Safe Defaults

- Chat scenario is enabled by default because it is read-heavy.
- Write-heavy appointment creation is disabled by default.
- To enable write flows explicitly:

```bash
ENABLE_WRITE_SCENARIOS=true k6 run load-tests/stress/stress.js
```

## Environment Variables

Copy the example file and customize it for EC2:

```bash
cp load-tests/.env.example load-tests/.env
```

Important variables:

- `BASE_URL`
- `API_PREFIX`
- `TENANT_EMAIL`
- `TENANT_PASSWORD`
- `LANDLORD_EMAIL`
- `LANDLORD_PASSWORD`
- `ROOM_IDS`
- `CHAT_ROOM_IDS`
- `ENABLE_CHAT_SCENARIO`
- `ENABLE_WRITE_SCENARIOS`
- `LOAD_DURATION`
- `SOAK_DURATION`

## How To Run

### Direct k6 commands

```bash
k6 run load-tests/smoke/smoke.js
```

```bash
k6 run load-tests/load/load.js
```

```bash
k6 run load-tests/stress/stress.js
```

```bash
k6 run load-tests/soak/soak.js
```

### Use the wrapper script

```bash
chmod +x load-tests/run.sh
./load-tests/run.sh smoke
./load-tests/run.sh load
./load-tests/run.sh stress
./load-tests/run.sh soak
```

### Override for AWS EC2

```bash
BASE_URL=http://YOUR_EC2_HOST ./load-tests/run.sh load
```

## Thresholds

All suites apply these default thresholds unless the script overrides them:

```javascript
http_req_failed: ["rate<0.01"]
http_req_duration: ["p(95)<500", "p(99)<1000"]
checks: ["rate>0.99"]
```

Stress uses a looser profile:

```javascript
http_req_failed: ["rate<0.05"]
http_req_duration: ["p(95)<1200", "p(99)<2500"]
checks: ["rate>0.95"]
```

## What To Watch While Tests Run

- Grafana panels listed in `load-tests/DASHBOARD_CHECKLIST.md`
- Prometheus target health
- Node Exporter for host CPU, RAM, Disk IO, and Network
- cAdvisor for `api`, `postgres`, and `redis` containers
- Loki logs for API errors and database spikes

## Notes

- If your production environment already has stable room IDs, set `ROOM_IDS` to avoid bootstrap misses.
- If your tenant account already has live chat rooms, set `CHAT_ROOM_IDS` to make chat checks deterministic.
- If your public room catalog is empty, smoke and browse tests will skip room detail requests automatically.
