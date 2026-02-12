\c postgres

DROP DATABASE IF EXISTS store_main;
CREATE DATABASE store_main;

\c store_main;

DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name       TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE products (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        TEXT NOT NULL,
  category_id BIGINT NOT NULL REFERENCES categories(id),
  price       NUMERIC(10,2) NOT NULL,
  sku         TEXT NOT NULL UNIQUE,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO categories (name)
VALUES
  ('Eletrônicos'),
  ('Acessórios'),
  ('Casa e Cozinha'),
  ('Papelaria');

INSERT INTO products (name, category_id, price, sku, is_active)
VALUES
  ('Fone Bluetooth Wave',
    (SELECT id FROM categories WHERE name='Acessórios'),
    129.90, 'AC-FONE-WAVE', TRUE),

  ('Carregador USB-C 20W',
    (SELECT id FROM categories WHERE name='Acessórios'),
    79.90, 'AC-CHARGER-20W', TRUE),

  ('Cabo USB-C 2m',
    (SELECT id FROM categories WHERE name='Acessórios'),
    49.90, 'AC-CABO-USBC-2M', TRUE),

  ('Mouse Sem Fio Orbit',
    (SELECT id FROM categories WHERE name='Eletrônicos'),
    89.90, 'EL-MOUSE-ORBIT', TRUE),

  ('Teclado Mecânico Compact',
    (SELECT id FROM categories WHERE name='Eletrônicos'),
    219.90, 'EL-TECLADO-COMPACT', TRUE),

  ('Lâmpada LED Smart',
    (SELECT id FROM categories WHERE name='Casa e Cozinha'),
    119.90, 'CC-LAMP-SMART', TRUE),

  ('Garrafa Térmica Inox 750ml',
    (SELECT id FROM categories WHERE name='Casa e Cozinha'),
    159.90, 'CC-GARRAFA-750', TRUE),

  ('Kit Organizadores (3 peças)',
    (SELECT id FROM categories WHERE name='Casa e Cozinha'),
    139.90, 'CC-ORG-3PCS', TRUE),

  ('Caderno A5 Pontilhado',
    (SELECT id FROM categories WHERE name='Papelaria'),
    39.90, 'PP-CAD-A5-DOT', TRUE),

  ('Caneta Gel 0.7mm (azul)',
    (SELECT id FROM categories WHERE name='Papelaria'),
    14.90, 'PP-CAN-GEL-07-AZ', TRUE),

  ('Planner Semanal',
    (SELECT id FROM categories WHERE name='Papelaria'),
    59.90, 'PP-PLAN-SEMANAL', TRUE),

  ('Adaptador P2 para P3',
    (SELECT id FROM categories WHERE name='Acessórios'),
    19.90, 'AC-ADAPT-P2P3', FALSE);
