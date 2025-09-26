# TITLE

TODO: add description and title

## Set up Podman (Preferred)

- Ubuntu: `sudo apt install podman podman-compose`
  - If you have installed docker, set the compose provider for podman: `export PODMAN_COMPOSE_PROVIDER=podman-compose`
- MacOS: `brew install podman podman-compose` then `podman machine init` and `podman machine start`. This starts a very small Linux VM that you can stop with `podman machine stop`. You do not need any further setup commands as we neither need root nor the docker api.

## Alternative: set up Docker (not recommended)

- Ubuntu: Follow instructions here: https://docs.docker.com/engine/install/ubuntu/ and https://docs.docker.com/engine/install/linux-postinstall/

## Docker: Running from docker-compose.yml

### Run with docker-compose.yml

- Start containers: `podman compose up -d` (currently fails)
# Docker: Running from docker-compose.yml

## Run with docker-compose.yml

- Start containers: `podman compose up -d`
  - With Docker: `docker compose up -d`

### SQL Dump

- Import sql file to database: `podman exec -it kibad-postgres bash -c "gzip -cd /tmp/data/2025-08-19_pg-faktencheck_dump.sql.gz | psql -U postgres -d kibad"`
  - With Docker: `docker exec -it kibad-postgres bash -c "gzip -cd /tmp/data/2025-08-19_pg-faktencheck_dump.sql.gz | psql -U postgres -d kibad"`

### Access pgAdmin

- Go to: http://localhost:8080
- Use login email "admin@admin.com" and pw "kibad" (see docker-compose!)
- Click "Add new server"
  - General -> Name: "Postgres-Local"
  - Connection
    - Host name/address: "kibad-postgres"
    - Port: 5432
    - Username: "postgres" (see docker-compose!)
    - Password: "kibad" (see docker-compose!)
- Access tables: Servers -> Postgres-Local -> Databases -> kibad -> Schemas -> public -> Tables

### Stop containers

## Stop containers

- Start containers: `podman compose down`
  - With Docker: `docker compose down`

## Deprecated - Docker: Running from scratch

### Postgres

- Download postgres: `docker pull postgres:latest`
- Create postgres container: `docker run --name kibad-postgres -e POSTGRES_PASSWORD=kibad -p 5432:5432 -d postgres`
- Create kibad database: `docker exec -it kibad-postgres psql -U postgres -c "CREATE DATABASE kibad"`

### SQL Dump

- Copy sql file to container: `docker cp directory_containing_sql_dump/2025-08-19_pg-faktencheck_dump.sql kibad-postgres:/2025-08-19_pg-faktencheck_dump.sql`
- Import sql file to database: `docker exec -it kibad-postgres psql -U postgres -d kibad -f /2025-08-19_pg-faktencheck_dump.sql`

### pgAdmin

- Create pgadmin container: `docker run --name kibad-pgadmin -e PGADMIN_DEFAULT_EMAIL=admin@admin.com -e PGADMIN_DEFAULT_PASSWORD=kibad -p 8080:80 -d dpage/pgadmin4`

### Network

- Create network: `docker network create kibad-network`
- Connect postgres: `docker network connect kibad-network kibad-postgres`
- Connect pgadmin: `docker network connect kibad-network kibad-pgadmin`

### Access pgAdmin

- Go to: http://localhost:8080
- Use login email "admin@admin.com" and pw "kibad"
- Click "Add new server"
  - General -> Name: "Postgres-Local"
  - Connection
    - Host name/address: "kibad-postgres"
    - Port: 5432
    - Username: "postgres"
    - Password: "kibad"
- Access tables: Servers -> Postgres-Local -> Databases -> kibad -> Schemas -> public -> Tables
