# Service EC (NestJS + PostgreSQL)

API service for E-commerce domain with CRUD endpoints for categories, products, users, orders, and order items. Uses PostgreSQL via TypeORM and supports per-entity faker generation endpoints.

## Requirements
- Node.js >= 20
- PostgreSQL

## Setup
1. Install dependencies:

```bash
cd apps/service-ec
npm install
```

2. Create `.env` file in `apps/service-ec`:

```dotenv
# App
PORT=3000

# Database
# service-ec is a write service, so it must connect to the primary node.
# If you run PostgreSQL from infra/docker on the host machine, keep localhost:5432.
DB_HOST=localhost
DB_PORT=5432
DB_USER=cmicadmin
DB_PASSWORD=Scuti@12345
DB_NAME=db_ec

# Optional
DB_SSL=false
DB_SYNC=false
DB_LOGGING=false
```

If `service-ec` runs inside Docker on the same compose network, use:

```dotenv
DB_HOST=postgres-primary
DB_PORT=5432
DB_USER=cmicadmin
DB_PASSWORD=Scuti@12345
DB_NAME=db_ec
```

3. Run the service:

```bash
npm run start:dev
```

## API Endpoints
Base URL: `/api`

### Categories
- `POST /api/categories`
- `GET /api/categories`
- `GET /api/categories/:id`
- `PATCH /api/categories/:id`
- `DELETE /api/categories/:id`
- `POST /api/categories/faker?count=10`

### Products
- `POST /api/products`
- `GET /api/products`
- `GET /api/products/:id`
- `PATCH /api/products/:id`
- `DELETE /api/products/:id`
- `POST /api/products/faker?count=20`

### Users
- `POST /api/users`
- `GET /api/users`
- `GET /api/users/:id`
- `PATCH /api/users/:id`
- `DELETE /api/users/:id`
- `POST /api/users/faker?count=20`

### Orders
- `POST /api/orders`
- `GET /api/orders`
- `GET /api/orders/:id`
- `PATCH /api/orders/:id`
- `DELETE /api/orders/:id`
- `POST /api/orders/faker?count=10`

### Order Items
- `POST /api/order-items`
- `GET /api/order-items`
- `GET /api/order-items/:id`
- `PATCH /api/order-items/:id`
- `DELETE /api/order-items/:id`
- `POST /api/order-items/faker?count=30&maxItemsPerOrder=4`

## Recommended Seeding Order
1. `POST /api/categories/faker`
2. `POST /api/products/faker`
3. `POST /api/users/faker`
4. `POST /api/orders/faker`
5. `POST /api/order-items/faker`

## Notes
- Faker endpoints require existing FK data (e.g. products require categories, orders require users, order items require orders and products).
- Faker is loaded via dynamic import to avoid ESM/CommonJS runtime errors with `ts-node-dev`.
- `DB_SYNC=true` will auto-create tables from TypeORM entities. Use with caution in production.
