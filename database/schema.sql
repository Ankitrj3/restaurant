-- =============================================
-- Restaurant Competitor Intelligence Platform
-- PostgreSQL Database Schema
-- =============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------------------------
-- 1. Restaurants
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS restaurants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    address         TEXT NOT NULL,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    distance_miles  DOUBLE PRECISION,
    rating          NUMERIC(2,1),
    total_reviews   INTEGER DEFAULT 0,
    price_category  VARCHAR(10),            -- $, $$, $$$, $$$$
    phone           VARCHAR(30),
    website         VARCHAR(500),
    is_client       BOOLEAN DEFAULT FALSE,
    delivery_available BOOLEAN DEFAULT TRUE,
    opening_hours   JSONB,
    delivery_platforms TEXT[],              -- {'UberEats','DoorDash','Grubhub'}
    cuisine_tags    TEXT[],
    image_url       VARCHAR(500),
    source          VARCHAR(50),            -- google, yelp, manual
    radius_group    VARCHAR(20),            -- '3mi', '5mi', '10mi', etc.
    raw_data        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------
-- 2. Menu Items
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS menu_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id   UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    item_name       VARCHAR(255) NOT NULL,
    category        VARCHAR(100),           -- Biryani, Curry, Tandoori, etc.
    description     TEXT,
    price           NUMERIC(8,2),
    is_veg          BOOLEAN,
    is_popular      BOOLEAN DEFAULT FALSE,
    is_signature    BOOLEAN DEFAULT FALSE,
    is_bestseller   BOOLEAN DEFAULT FALSE,
    spice_level     VARCHAR(20),
    image_url       VARCHAR(500),
    source          VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant ON menu_items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category);

-- -------------------------------------------
-- 3. Offers & Promotions
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS offers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id   UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    offer_type      VARCHAR(50),            -- coupon, bogo, combo, etc.
    title           VARCHAR(255),
    description     TEXT,
    discount_percent NUMERIC(5,2),
    discount_amount  NUMERIC(8,2),
    min_order_amount NUMERIC(8,2),
    code            VARCHAR(50),
    platform        VARCHAR(50),            -- UberEats, DoorDash, etc.
    valid_from      TIMESTAMPTZ,
    valid_until     TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE,
    source          VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_offers_restaurant ON offers(restaurant_id);

-- -------------------------------------------
-- 4. Comparison Results (cached)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS comparisons (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id   UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    price_comparison        JSONB,
    offer_comparison        JSONB,
    menu_comparison         JSONB,
    customer_attraction     JSONB,
    competitor_better_areas JSONB,
    client_better_areas     JSONB,
    recommendations         JSONB,
    scores                  JSONB,
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------
-- 5. Market Analysis (cached)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS market_analysis (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type   VARCHAR(50),
    data            JSONB,
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------
-- 6. AI Recommendations Log
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category        VARCHAR(50),            -- pricing, offers, menu, sales
    recommendation  TEXT,
    priority        VARCHAR(20),            -- high, medium, low
    details         JSONB,
    is_implemented  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------
-- 7. Platform Menu Items (per-platform pricing)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS platform_menu_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id   UUID REFERENCES restaurants(id) ON DELETE CASCADE,
    restaurant_name VARCHAR(255) NOT NULL,
    item_name       VARCHAR(255) NOT NULL,
    item_name_normalized VARCHAR(255),
    category        VARCHAR(100),
    platform        VARCHAR(30) NOT NULL,   -- instore, ubereats, doordash, grubhub
    price           NUMERIC(8,2),
    is_available    BOOLEAN DEFAULT TRUE,
    markup_over_instore NUMERIC(8,2),
    description     TEXT,
    is_veg          BOOLEAN,
    source          VARCHAR(50),
    fetched_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_platform_menu_restaurant ON platform_menu_items(restaurant_name, platform);
CREATE INDEX IF NOT EXISTS idx_platform_menu_category ON platform_menu_items(category);
CREATE INDEX IF NOT EXISTS idx_platform_menu_item ON platform_menu_items(item_name_normalized);

-- -------------------------------------------
-- 8. Delivery Fees (per-platform snapshots)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS delivery_fees (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_name VARCHAR(255) NOT NULL,
    platform        VARCHAR(30) NOT NULL,
    delivery_fee    NUMERIC(8,2),
    service_fee     NUMERIC(8,2),
    surge_fee       NUMERIC(8,2),
    tax_estimate    NUMERIC(8,2),
    free_delivery_threshold NUMERIC(8,2),
    min_order_amount NUMERIC(8,2),
    estimated_delivery_time VARCHAR(50),
    fetched_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_delivery_fees_restaurant ON delivery_fees(restaurant_name, platform);

-- -------------------------------------------
-- 9. Comparison Cache (TTL-based)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS comparison_cache (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comparison_type VARCHAR(50) NOT NULL,
    params_hash     VARCHAR(64) NOT NULL,
    result_data     JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    UNIQUE(comparison_type, params_hash)
);

CREATE INDEX IF NOT EXISTS idx_comparison_cache_lookup ON comparison_cache(comparison_type, params_hash);

-- -------------------------------------------
-- Insert client restaurant
-- -------------------------------------------
INSERT INTO restaurants (name, address, latitude, longitude, distance_miles, rating, is_client, price_category)
VALUES (
    'Bawarchi Indian Cuisine & Bar Leander',
    '15881 Ronald Reagan Blvd #5, Leander, TX 78641, United States',
    30.5680447,
    -97.8029374,
    0,
    4.3,
    TRUE,
    '$$'
) ON CONFLICT DO NOTHING;
