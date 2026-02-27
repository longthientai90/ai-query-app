create table if not exists categories
(
    id          bigserial
        primary key,
    name        varchar(255) not null,
    description text,
    created_at  timestamp default now(),
    updated_at  timestamp default now()
);

alter table categories
    owner to cmicadmin;

grant select on categories to mcp_readonly;

create table if not exists products
(
    id          bigserial
        primary key,
    name        varchar(255)   not null,
    category_id bigint
                               references categories
                                   on delete set null,
    adjective   varchar(255),
    material    varchar(255),
    price       numeric(12, 2) not null
        constraint products_price_check
            check (price >= (0)::numeric),
    description text,
    created_at  timestamp default now(),
    updated_at  timestamp default now()
);

alter table products
    owner to cmicadmin;

create index if not exists idx_products_category_id
    on products (category_id);

grant select on products to mcp_readonly;

create table if not exists users
(
    id            bigserial
        primary key,
    email         varchar(255) not null
        unique,
    password_hash text         not null,
    first_name    varchar(100),
    last_name     varchar(100),
    phone         varchar(30),
    is_active     boolean   default true,
    created_at    timestamp default now(),
    updated_at    timestamp default now()
);

alter table users
    owner to cmicadmin;

grant select on users to mcp_readonly;

create table if not exists orders
(
    id           bigserial
        primary key,
    user_id      bigint                   not null
        references users
            on delete cascade,
    status       varchar(50)    default 'pending'::character varying,
    total_amount numeric(12, 2) default 0 not null,
    created_at   timestamp      default now(),
    updated_at   timestamp      default now()
);

alter table orders
    owner to cmicadmin;

create index if not exists idx_orders_user_id
    on orders (user_id);

grant select on orders to mcp_readonly;

create table if not exists order_items
(
    id         bigserial
        primary key,
    order_id   bigint         not null
        references orders
            on delete cascade,
    product_id bigint         not null
        references products,
    quantity   integer        not null
        constraint order_items_quantity_check
            check (quantity > 0),
    unit_price numeric(12, 2) not null,
    created_at timestamp default now()
);

alter table order_items
    owner to cmicadmin;

create index if not exists idx_order_items_order_id
    on order_items (order_id);

create index if not exists idx_order_items_product_id
    on order_items (product_id);

grant select on order_items to mcp_readonly;

