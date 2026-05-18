# Database Schema & ERD

## Architecture Decisions
- **Soft Delete**: Implemented via an `is_deleted` boolean flag and `deleted_at` timestamp.
- **Audit Timestamps**: `created_at` and `updated_at` on every table.
- **Indexing**: 
  - GIN indexes with `pg_trgm` on `Room.title` and `Room.description` to avoid slow `LIKE '%keyword%'` queries.
  - B-Tree indexes on frequently filtered columns (`district`, `ward`, `price`, `area`, `status`).
  - Spatial searches: For this scope, we use simple latitude/longitude bounding box queries or PostGIS (if installed, though standard indexing on lat/lng with simple math works for small scales).

## Entity Relationship Diagram (Mermaid)

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email UK
        string password_hash
        string role "TENANT, LANDLORD, ADMIN"
        boolean is_active
        boolean is_deleted
        datetime created_at
        datetime updated_at
    }

    PROFILES {
        uuid id PK
        uuid user_id FK
        string full_name
        string phone
        string avatar_url
        text bio
        datetime created_at
        datetime updated_at
    }

    ROOMS {
        uuid id PK
        uuid landlord_id FK
        string title
        text description
        decimal monthly_price
        decimal deposit
        decimal electric_price
        decimal water_price
        float area
        int max_people
        string gender_preference
        date available_date
        string province
        string district
        string ward
        string full_address
        float latitude
        float longitude
        jsonb amenities
        jsonb rules
        string status "DRAFT, PENDING, APPROVED, REJECTED, HIDDEN, RENTED"
        boolean is_deleted
        datetime created_at
        datetime updated_at
    }

    ROOM_IMAGES {
        uuid id PK
        uuid room_id FK
        string image_url
        int sort_order
        datetime created_at
    }

    FAVORITES {
        uuid id PK
        uuid tenant_id FK
        uuid room_id FK
        datetime created_at
    }

    CHAT_ROOMS {
        uuid id PK
        uuid tenant_id FK
        uuid landlord_id FK
        uuid room_id FK
        datetime created_at
    }

    CHAT_MESSAGES {
        uuid id PK
        uuid chat_room_id FK
        uuid sender_id FK
        text content
        string message_type "TEXT, IMAGE"
        string status "SENT, DELIVERED, READ"
        datetime created_at
    }

    APPOINTMENTS {
        uuid id PK
        uuid tenant_id FK
        uuid landlord_id FK
        uuid room_id FK
        datetime scheduled_time
        string status "PENDING, ACCEPTED, REJECTED, DONE"
        text note
        datetime created_at
        datetime updated_at
    }

    NOTIFICATIONS {
        uuid id PK
        uuid user_id FK
        string title
        text body
        string type
        jsonb data
        boolean is_read
        datetime created_at
    }

    USERS ||--o| PROFILES : "has"
    USERS ||--o{ ROOMS : "creates (landlord)"
    ROOMS ||--o{ ROOM_IMAGES : "contains"
    USERS ||--o{ FAVORITES : "saves"
    ROOMS ||--o{ FAVORITES : "is_saved"
    USERS ||--o{ CHAT_ROOMS : "participates"
    CHAT_ROOMS ||--o{ CHAT_MESSAGES : "contains"
    USERS ||--o{ APPOINTMENTS : "requests/manages"
    ROOMS ||--o{ APPOINTMENTS : "is_viewed"
    USERS ||--o{ NOTIFICATIONS : "receives"
```

## Redis Keys
- **Search Cache**: `room:search:{query_hash}` -> JSON (TTL: 120s)
- **Room Detail Cache**: `room:detail:{id}` -> JSON (TTL: 300s)
- **User Online Status**: `user:online:{id}` -> Timestamp (TTL: 60s)
- **Typing Indicator**: `chat:typing:{chat_room_id}:{user_id}` -> bool (TTL: 5s)
- **Favorite Counter**: `room:favorites:{id}` -> int
- **View Counter**: `room:views:{id}` -> int
- **Token Blacklist**: `jwt:blacklist:{jti}` -> bool (TTL: expiration)
