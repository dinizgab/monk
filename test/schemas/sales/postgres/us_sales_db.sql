CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS customers (
  id           BIGSERIAL PRIMARY KEY,
  email        CITEXT UNIQUE NOT NULL,
  full_name    TEXT NOT NULL,
  state        TEXT NOT NULL DEFAULT 'CA',
  sms_opt_in   BOOLEAN NOT NULL DEFAULT false,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
  id           BIGSERIAL PRIMARY KEY,
  customer_id  BIGINT NOT NULL REFERENCES customers(id),
  total_usd    NUMERIC(12,2) NOT NULL,
  coupon_code  TEXT,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO customers (email, full_name, state, sms_opt_in)
VALUES
  ('alice@example.com','Alice Braun','NY', true),
  ('carol@example.com','Carol Johnson','CA', false),
  ('dave@example.com','Dave Lee','TX', true),
  ('erika@example.com','Erika Kim','WA', true),
  ('frank@example.com','Frank Wright','FL', false),
  ('grace@example.com','Grace Hall','IL', true);

INSERT INTO customers (email, full_name, state, sms_opt_in)
SELECT
  format('us_user_%02s@example.com', g)           AS email,
  format('US User %02s', g)                       AS full_name,
  (ARRAY['CA','NY','TX','FL','IL','GA','MA','CO'])[(g % 8)+1] AS state,
  (g % 3 = 0)                                     AS sms_opt_in
FROM generate_series(1,14) AS t(g)
ON CONFLICT DO NOTHING;

WITH ids AS (
  SELECT
    (SELECT id FROM customers WHERE email='alice@example.com')  AS alice,
    (SELECT id FROM customers WHERE email='carol@example.com')  AS carol,
    (SELECT id FROM customers WHERE email='grace@example.com')  AS grace,
    (SELECT id FROM customers WHERE email='erika@example.com')  AS erika
)
INSERT INTO orders (customer_id, total_usd, coupon_code)
SELECT alice, 149.00, 'WELCOME10' FROM ids UNION ALL
SELECT alice, 79.99 , NULL        FROM ids UNION ALL
SELECT carol, 59.00 , 'TRY10'     FROM ids UNION ALL
SELECT grace, 499.00, 'VIP25'     FROM ids UNION ALL
SELECT erika, 89.00 , NULL        FROM ids;

INSERT INTO orders (customer_id, total_usd, coupon_code)
SELECT c.id,
       25 + (g * 4.20)::numeric(12,2) AS total_usd,
       CASE WHEN g % 4 = 0 THEN 'SPRING15' ELSE NULL END
FROM (
  SELECT id, row_number() over (order by id) AS rn
  FROM customers
  WHERE email LIKE 'us_user_%'
  ORDER BY id
  LIMIT 16
) c
JOIN generate_series(1,16) AS t(g) ON t.g = c.rn;

INSERT INTO orders (customer_id, total_usd, coupon_code)
SELECT id, 95.00, NULL
FROM customers
WHERE email IN ('dave@example.com','frank@example.com','grace@example.com');