DROP DATABASE IF EXISTS store_alt;
CREATE DATABASE store_alt;

\c store_alt;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS product_groups;

CREATE TABLE product_groups (
  gid        INTEGER PRIMARY KEY,
  group_name VARCHAR(255) NOT NULL,
  last_mod   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE items (
  code            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title           VARCHAR(255) NOT NULL,
  group_ref       INTEGER,
  amount_in_cents INTEGER NOT NULL,
  active          CHAR(1) NOT NULL DEFAULT 'Y',
  created_on      DATE NOT NULL DEFAULT CURRENT_DATE
);

INSERT INTO product_groups (gid, group_name)
VALUES
  (1, 'Eletrônicos'),
  (2, 'Acessórios'),
  (3, 'Casa e Cozinha'),
  (4, 'Papelaria');

INSERT INTO items (title, group_ref, amount_in_cents, active)
VALUES
  ('Fone Bluetooth Wave',            2,  12990, 'Y'),
  ('Carregador USB-C 20W',           2,   7990, 'Y'),
  ('Cabo USB-C 2m',                  2,   4990, 'Y'),
  ('Mouse Sem Fio Orbit',            1,   8990, 'Y'),
  ('Teclado Mecânico Compact',       1,  21990, 'Y'),
  ('Lâmpada LED Smart',              3,  11990, 'Y'),
  ('Garrafa Térmica Inox 750ml',     3,  15990, 'Y'),
  ('Kit Organizadores (3 peças)',    3,  13990, 'Y'),
  ('Caderno A5 Pontilhado',          4,   3990, 'Y'),
  ('Caneta Gel 0.7mm (azul)',        4,   1490, 'Y'),
  ('Planner Semanal',                4,   5990, 'Y'),
  ('Adaptador P2 para P3',           2,   1990, 'N');
