CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS customers (
  id           BIGSERIAL PRIMARY KEY,
  email        CITEXT UNIQUE NOT NULL,
  full_name    TEXT NOT NULL,
  country      TEXT NOT NULL DEFAULT 'DE',
  marketing_ok BOOLEAN NOT NULL DEFAULT false,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
  id           BIGSERIAL PRIMARY KEY,
  customer_id  BIGINT NOT NULL REFERENCES customers(id),
  total_eur    NUMERIC(12,2) NOT NULL,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  coupon_code  TEXT
);

INSERT INTO customers (email, full_name, country, marketing_ok)
VALUES
  ('alice@example.com','Alice Braun','DE', true),
  ('bob@example.com','Bob Martin','FR', false),
  ('carla@sample.eu','Carla Schmidt','DE', true),
  ('daniel@sample.eu','Daniel Rossi','IT', false),
  ('eva@sample.eu','Eva Novak','CZ', true),
  ('giulia@sample.eu','Giulia Conti','IT', true);

INSERT INTO customers (email, full_name, country, marketing_ok)
SELECT
  format('eu_user_%02s@example.com', g)            AS email,
  format('EU User %02s', g)                        AS full_name,
  (ARRAY['DE','FR','IT','ES','PT','PL','NL','AT'])[(g % 8)+1] AS country,
  (g % 2 = 0)                                      AS marketing_ok
FROM generate_series(1,14) AS t(g)
ON CONFLICT DO NOTHING;

WITH ids AS (
  SELECT
    (SELECT id FROM customers WHERE email='alice@example.com')  AS alice,
    (SELECT id FROM customers WHERE email='bob@example.com')    AS bob,
    (SELECT id FROM customers WHERE email='carla@sample.eu')    AS carla,
    (SELECT id FROM customers WHERE email='giulia@sample.eu')   AS giulia
)
INSERT INTO orders (customer_id, total_eur, coupon_code)
SELECT alice, 129.90, 'WELCOME10' FROM ids UNION ALL
SELECT alice, 59.50 , NULL        FROM ids UNION ALL
SELECT bob  , 39.99 , 'TRYAGAIN'  FROM ids UNION ALL
SELECT carla, 299.00, 'VIP20'     FROM ids UNION ALL
SELECT giulia, 89.00, NULL        FROM ids;

INSERT INTO orders (customer_id, total_eur, coupon_code)
SELECT c.id,
       20 + (g * 3.15)::numeric(12,2) AS total_eur,
       CASE WHEN g % 5 = 0 THEN 'NEW15' ELSE NULL END
FROM (
  SELECT id, row_number() over (order by id) AS rn
  FROM customers
  WHERE email LIKE 'eu_user_%'
  ORDER BY id
  LIMIT 16
) c
JOIN generate_series(1,16) AS t(g) ON t.g = c.rn;

INSERT INTO orders (customer_id, total_eur, coupon_code)
SELECT id, 75.00, NULL
FROM customers
WHERE email IN ('eva@sample.eu','daniel@sample.eu','carla@sample.eu');
