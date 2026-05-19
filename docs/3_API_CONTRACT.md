# API Contract

## 1. Authentication (`/api/v1/auth`)
- `POST /register`
  - Body: `{ email, password, full_name, phone, role }`
  - Response: `{ access_token, refresh_token, user: {...} }`
- `POST /login`
  - Body: `{ email, password }`
  - Response: `{ access_token, refresh_token, user: {...} }`
- `POST /logout`
  - Body: `{ refresh_token }`
  - Auth: Required. Adds token to Redis blacklist.
- `POST /refresh`
  - Body: `{ refresh_token }`
  - Response: `{ access_token }`

## 2. Profile (`/api/v1/profile`)
- `GET /me`
  - Auth: Required
  - Response: `{ id, email, role, profile: { full_name, phone, avatar_url, bio } }`
- `PUT /me`
  - Body: `{ full_name, phone, bio }`
- `POST /avatar/presigned-url`
  - Response: `{ upload_url, file_url, object_key }`

## 3. Room Management (`/api/v1/rooms`)
- `POST /` (Landlord only)
  - Body: `{ title, description, price, area, address, amenities, rules, images... }`
  - Response: `201 Created`, Room object
- `PUT /{id}` (Landlord only)
  - Body: Partial update payload
- `DELETE /{id}` (Landlord only)
  - Action: Soft delete
- `POST /{id}/status` (Landlord/Admin)
  - Body: `{ status }`

## 4. Room Search & Listing (`/api/v1/search`)
- `GET /rooms`
  - Query Params: `keyword, district, ward, min_price, max_price, min_area, max_area, gender, cursor, limit`
  - Response: `{ data: [...], next_cursor: "..." }`
  - Cache: Redis `room:search:{query}`
- `GET /rooms/{id}`
  - Response: Complete room details including landlord info, favorite count (from Redis), view count.
  - Cache: Redis `room:detail:{id}`

## 5. Favorites (`/api/v1/favorites`)
- `POST /rooms/{id}/favorite` (Tenant only)
  - Action: Adds to DB, increments Redis counter
- `DELETE /rooms/{id}/favorite` (Tenant only)
  - Action: Removes from DB, decrements Redis counter
- `GET /`
  - Response: List of favorite rooms for the user

## 6. Chat & Real-time (WebSocket)
### 6.1 REST API (`/api/v1/chat`)

#### Common
- Auth: Required (JWT Bearer)
- Cursor pagination: `next_cursor` is an opaque string (client must pass it back as `cursor`)
- Default `limit=20`, max `limit=50`

#### 1) Create / Get existing room
- `POST /rooms`
- Body: `{ "room_id": "uuid" }`
- Behavior:
  - Find landlord by `rooms.landlord_id`
  - Create chat room if not exists for `(tenant, landlord, room)`
  - Must not create duplicates
- Response:
  - `200 OK`
  - `{ "success": true, "chat_room": { "id": "uuid", "room": { "id": "uuid" }, "participant": { "id": "uuid", "full_name": "", "avatar_url": "" } }, "is_existing": true }`

#### 2) Inbox (room list)
- `GET /rooms`
- Query params:
  - `cursor` (optional)
  - `limit` (optional)
  - `filter` (optional): `all` | `unread` (default `all`)
- Sort: `last_message_at DESC NULLS LAST`, tie-breaker by id DESC
- Response:
  - `200 OK`
  - `{ "data": [ { "id": "uuid", "participant": { "id": "uuid", "full_name": "", "avatar_url": "", "is_online": true }, "room": { "id": "uuid", "title": "", "thumbnail": "" }, "last_message": { "id": "uuid", "content": "", "created_at": "" }, "unread_count": 2 } ], "next_cursor": "" }`

#### 3) Room detail metadata
- `GET /rooms/{chat_room_id}`
- Response:
  - `200 OK`
  - `{ "id": "uuid", "participant": { "id": "uuid", "full_name": "", "avatar_url": "", "is_online": true }, "room": { "id": "uuid", "title": "", "thumbnail": "" }, "is_blocked": false }`

#### 4) Message history (REST only)
- `GET /rooms/{chat_room_id}/messages`
- Query params:
  - `cursor` (optional)
  - `limit` (optional)
  - `before_message_id` (optional, uuid)
- Sort: newest first
- Response:
  - `200 OK`
  - `{ "data": [ { "id": "uuid", "sender_id": "uuid", "message_type": "TEXT", "content": "Hello", "image_url": null, "is_read": true, "created_at": "" } ], "next_cursor": "" }`

#### 5) Mark read
- `POST /rooms/{chat_room_id}/read`
- Body: `{ "message_id": "uuid" }`
- Behavior:
  - Update participant `last_read_at`
  - Mark unread messages as read for the user
  - Broadcast websocket event `seen`
- Response: `{ "success": true }`

#### 6) Total unread count (badge)
- `GET /unread-count`
- Response: `{ "count": 12 }`

#### 7) Presigned URL for chat images
- `POST /image/presigned-url`
- Response: `{ "upload_url": "", "file_url": "", "object_key": "" }`
- Folder/key prefix: `chat/`

#### 8) Delete chat room (per-user soft delete)
- `DELETE /rooms/{chat_room_id}`
- Response: `{ "success": true }`

#### 9) Block user in room
- `POST /rooms/{chat_room_id}/block`
- Response: `{ "success": true }`

#### 10) Report user
- `POST /report`
- Body: `{ "chat_room_id": "uuid", "reason": "spam" }`
- Response: `{ "success": true }`

### 6.2 WebSocket (`/ws/chat/{chat_room_id}`)

#### Auth
- Token supported via:
  - Query param: `?token=...`
  - Header: `Authorization: Bearer ...`
- Only room participants can connect; blocked users are rejected.

#### Client → Server events
- `send_message`
  - `{ "type": "send_message", "temp_id": "uuid", "message_type": "TEXT", "content": "Hello" }`
  - `{ "type": "send_message", "temp_id": "uuid", "message_type": "IMAGE", "image_url": "https://..." }`
- `typing`
  - `{ "type": "typing", "is_typing": true }`
- `read_receipt`
  - `{ "type": "read_receipt", "message_id": "uuid" }`

#### Server → Client events
- `new_message`
  - `{ "type": "new_message", "data": { "id": "uuid", "temp_id": "uuid", "sender_id": "uuid", "message_type": "TEXT", "content": "", "image_url": null, "created_at": "" } }`
- `typing`
  - `{ "type": "typing", "user_id": "uuid", "is_typing": true }`
- `seen`
  - `{ "type": "seen", "message_id": "uuid", "user_id": "uuid" }`
- `online_status`
  - `{ "type": "online_status", "user_id": "uuid", "is_online": true }`
- `error`
  - `{ "type": "error", "message": "Unauthorized" }`

## 7. Appointments (`/api/v1/appointments`)
- `POST /` (Tenant)
  - Body: `{ room_id, scheduled_time, note }`
- `PUT /{id}/status` (Landlord)
  - Body: `{ status: "ACCEPTED" | "REJECTED" | "DONE" }`

## 8. Admin Panel (`/api/v1/admin`)
- `POST /rooms/{id}/approve`
- `POST /rooms/{id}/reject`
- `POST /users/{id}/ban`
