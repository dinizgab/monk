DROP DATABASE IF EXISTS app;
CREATE DATABASE app;

\c app;

DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email    TEXT NOT NULL UNIQUE
);

CREATE TABLE posts (
  id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  content TEXT NOT NULL,
  user_id BIGINT NOT NULL REFERENCES users(id)
);

INSERT INTO users (id, username, email) VALUES
  (1, 'alice', 'alice@gmail.com'),
  (2, 'bob', 'bob@email.com'),
  (3, 'carol', 'carol@email.com'),
  (4, 'dave', 'dave@gmail.com'),
  (5, 'eve', 'eve@email.com'),
  (6, 'frank', 'frank@gmail.com'),
  (7, 'grace', 'grace@email.com'),
  (8, 'heidi', 'heidi@gmail.com'),
  (9, 'ivan', 'ivan@gmail.com'),
  (10, 'judy', 'judy@email.com');

INSERT INTO posts (content, user_id) VALUES
  ('Primeiro post da Alice', 1),
  ('Alice gosta de banco de dados', 1),
  ('Bob explorando PostgreSQL', 2),
  ('Bob falando sobre índices', 2),
  ('Carol estudando sistemas distribuídos', 3),
  ('Carol escrevendo sobre concorrência', 3),
  ('Dave entrou na plataforma', 4),
  ('Dave aprendendo SQL', 4),
  ('Eve gosta de segurança da informação', 5),
  ('Eve escrevendo sobre autenticação', 5),
  ('Frank falando de APIs REST', 6),
  ('Frank comparando GraphQL e REST', 6),
  ('Grace discutindo microsserviços', 7),
  ('Grace escrevendo sobre escalabilidade', 7),
  ('Heidi estudando mensageria', 8),
  ('Heidi testando Kafka', 8),
  ('Ivan escrevendo sobre NoSQL', 9),
  ('Ivan comparando SQL e NoSQL', 9),
  ('Judy iniciando no desenvolvimento', 10),
  ('Judy aprendendo modelagem de dados', 10);