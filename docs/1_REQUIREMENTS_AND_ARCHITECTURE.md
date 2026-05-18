# Requirements and Architecture Analysis

## 1. Goal Overview
The goal is to build a high-performance, production-grade backend for a Rental House Platform (similar to Chợ Tốt, Facebook Marketplace, or Airbnb Lite). It supports multi-role users (Tenant, Landlord, Admin), real-time chat, background tasks, complex search with caching, and push notifications.

## 2. Technology Stack & Trade-offs
- **Framework**: Django (ASGI mode)
- **API Layer**: Django Ninja. *Trade-off*: Standard Django REST Framework (DRF) relies heavily on the Django ORM and does not natively support Pydantic v2 or async as elegantly as Django Ninja. Ninja provides seamless async support and Pydantic v2 integration out-of-the-box.
- **Database**: PostgreSQL with SQLAlchemy 2.0 (Async) + Alembic. *Trade-off*: We are bypassing Django's built-in ORM. This means we lose Django's Admin panel out-of-the-box for these models, but we gain the massive flexibility, performance, and explicit async transaction management of SQLAlchemy 2.0.
- **Caching & Real-time**: Redis. Used for search caching, JWT blacklisting, rate limiting, and WebSocket connection state.
- **Background Jobs**: Celery + Redis broker. *Trade-off*: Celery is synchronous by nature, but we can wrap async calls inside synchronous tasks using `asyncio.run()`, or keep background tasks purely synchronous while the web layer is async.
- **Deployment**: Fully containerized using Docker, docker-compose, and Nginx as a reverse proxy.

## 3. Clean Architecture Implementation
We follow a strict Clean Architecture pattern to separate concerns and ensure maintainability:

1. **API / Controllers (`app/api/`)**: Handlers for HTTP requests (using Django Ninja routers). They validate input via Pydantic (`app/schemas/`) and pass data to the Service layer. NO business logic here.
2. **Services (`app/services/`)**: The core business logic layer. Services orchestrate operations, enforce business rules, and call repositories. They are decoupled from the HTTP context.
3. **Repositories (`app/repositories/`)**: The data access layer. They encapsulate SQLAlchemy async sessions and abstract away database queries. Services call Repositories to get or save data.
4. **Models (`app/models/`)**: SQLAlchemy declarative base models representing database tables.
5. **Schemas (`app/schemas/`)**: Pydantic v2 models for request/response validation and internal data transfer objects (DTOs).

## 4. Data Flow
`Request -> Nginx -> Django ASGI -> Django Ninja Router (Pydantic Validation) -> Service Layer -> Repository Layer -> SQLAlchemy -> PostgreSQL`

## 5. Security & Observability
- **Auth**: Stateless JWT (Access/Refresh) with Redis-backed blacklisting for logout.
- **RBAC**: Role-based access control (Admin, Landlord, Tenant) enforced via custom decorators at the API layer.
- **Logging**: Structured JSON logging to stdout, picked up by Docker. OpenTelemetry traces can be injected into the ASGI middleware.
