# Monk - A NL2SQL translator

## Test containers commands
```
--------------------------------
mysql:
docker run -d --name mysql \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=appdb \
  -p 3306:3306 \
  -v mysql_data:/var/lib/mysql \
  --restart unless-stopped \
  mysql
--------------------------------
psql:
docker run -d \
  --name pg \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=apppass \
  -e POSTGRES_DB=appdb \
  -p 5432:5432 \
  postgres
--------------------------------
```