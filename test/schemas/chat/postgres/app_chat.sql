\c postgres

DROP DATABASE IF EXISTS app_chat;
CREATE DATABASE app_chat;

\c app_chat;

DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS chat_members;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  username  TEXT NOT NULL UNIQUE,
  full_name TEXT
);

CREATE TABLE chats (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        TEXT NOT NULL,
  description TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_members (
  user_id   BIGINT NOT NULL REFERENCES users(id),
  chat_id   BIGINT NOT NULL REFERENCES chats(id),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, chat_id)
);

CREATE TABLE messages (
  id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  content   TEXT NOT NULL,
  sended_by BIGINT NOT NULL REFERENCES users(id),
  chat_id   BIGINT NOT NULL REFERENCES chats(id),
  sended_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO users (username, full_name) VALUES
  ('alice', 'Alice Silva'),
  ('bob',   'Bob Santos'),
  ('carol', 'Carol Pereira'),
  ('dave',  'Dave Oliveira'),
  ('eve',   'Eve Costa'),
  ('frank', 'Frank Rodrigues'),
  ('grace', 'Grace Almeida'),
  ('heidi', 'Heidi Nogueira'),
  ('ivan',  'Ivan Ribeiro'),
  ('judy',  'Judy Martins');


INSERT INTO chats (name, description) VALUES
  ('Geral', 'Chat geral da aplicação'),
  ('Backend', 'Discussões sobre backend'),
  ('Banco de Dados', 'SQL, NoSQL e afins'),
  ('Arquitetura', 'Padrões e boas práticas'),
  ('Off-topic', 'Conversas aleatórias');

SELECT setval('chats_id_seq', 5, true);

INSERT INTO chat_members (user_id, chat_id) VALUES
  -- Geral (todos)
  (1,1),(2,1),(3,1),(4,1),(5,1),
  (6,1),(7,1),(8,1),(9,1),(10,1),

  -- Backend
  (1,2),(2,2),(3,2),(6,2),(7,2),

  -- Banco de Dados
  (1,3),(2,3),(4,3),(8,3),(9,3),

  -- Arquitetura
  (3,4),(5,4),(6,4),(7,4),(10,4),

  -- Off-topic
  (2,5),(4,5),(8,5),(9,5);

-- Mensagens – Chat Geral
INSERT INTO messages (content, sended_by, chat_id) VALUES
  ('Bom dia, pessoal!', 1, 1),
  ('Alguém testando algo novo hoje?', 2, 1),
  ('Estou estudando concorrência', 3, 1),
  ('PostgreSQL é poderoso', 4, 1),
  ('Segurança nunca é demais', 5, 1),
  ('API bem feita salva vidas', 6, 1),
  ('Escalabilidade é um desafio real', 7, 1),
  ('Mensageria ajuda muito', 8, 1);

-- Mensagens – Backend
INSERT INTO messages (content, sended_by, chat_id) VALUES
  ('REST ainda domina?', 1, 2),
  ('Depende do caso', 2, 2),
  ('GraphQL resolve alguns problemas', 6, 2),
  ('Clean Architecture ajuda bastante', 7, 2);

-- Mensagens – Banco de Dados
INSERT INTO messages (content, sended_by, chat_id) VALUES
  ('SQL vs NoSQL, qual escolher?', 1, 3),
  ('Depende da carga e do modelo', 2, 3),
  ('Índices fazem muita diferença', 4, 3),
  ('Kafka não é banco 😅', 8, 3),
  ('Modelo relacional ainda é rei', 9, 3);

-- Mensagens – Arquitetura
INSERT INTO messages (content, sended_by, chat_id) VALUES
  ('DDD ainda vale a pena?', 3, 4),
  ('Quando bem aplicado, sim', 5, 4),
  ('Hexagonal facilita testes', 6, 4),
  ('Arquitetura ruim custa caro', 7, 4),
  ('Começar simples é melhor', 10, 4);

-- Mensagens – Off-topic
INSERT INTO messages (content, sended_by, chat_id) VALUES
  ('Café ou chá?', 2, 5),
  ('Café sempre', 4, 5),
  ('Depende do dia', 8, 5),
  ('Qualquer coisa com açúcar', 9, 5);