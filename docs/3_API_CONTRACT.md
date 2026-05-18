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
- `WS /ws/chat/{room_id}`
  - Auth: Token required in query param or initial message.
  - Payloads:
    - `{ type: "message", content: "..." }`
    - `{ type: "typing", is_typing: true }`
    - `{ type: "read_receipt", message_id: "..." }`

## 7. Appointments (`/api/v1/appointments`)
- `POST /` (Tenant)
  - Body: `{ room_id, scheduled_time, note }`
- `PUT /{id}/status` (Landlord)
  - Body: `{ status: "ACCEPTED" | "REJECTED" | "DONE" }`

## 8. Admin Panel (`/api/v1/admin`)
- `POST /rooms/{id}/approve`
- `POST /rooms/{id}/reject`
- `POST /users/{id}/ban`
