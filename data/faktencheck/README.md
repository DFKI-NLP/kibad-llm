# Running from scratch
## Postgres
- Download postgres: `docker pull postgres:latest`
- Create postgres container: `docker run --name kibad-postgres -e POSTGRES_PASSWORD=kibad -p 5432:5432 -d postgres`
- Create kibad database: `docker exec -it kibad-postgres psql -U postgres -c "CREATE DATABASE kibad"`

## SQL Dump
- Copy sql file to container: `docker cp directory_containing_sql_dump/2025-08-19_pg-faktencheck_dump.sql kibad-postgres:/2025-08-19_pg-faktencheck_dump.sql`
- Import sql file to database: `docker exec -it kibad-postgres psql -U postgres -d kibad -f /2025-08-19_pg-faktencheck_dump.sql`

## pgAdmin
- Create pgadmin container: `docker run --name kibad-pgadmin -e PGADMIN_DEFAULT_EMAIL=admin@admin.com -e PGADMIN_DEFAULT_PASSWORD=kibad -p 8080:80 -d dpage/pgadmin4`

## Network
- Create network: `docker network create kibad-network`
- Connect postgres: `docker network connect kibad-network kibad-postgres`
- Connect pgadmin: `docker network connect kibad-network kibad-pgadmin`

## Access pgAdmin
- Go to: http://localhost:8080
- Click "Add new server"
    - General -> Name: "Postgres-Local"
    - Connection
        - Host name/address: "kibad-postgres"
        - Port: 5432
        - Username: "postgres"
        - Password: "kibad"
- Access tables: Servers -> Postgres-Local -> Databases -> kibad -> Schemas -> public -> Tables

# Running from docker-compose.yml
## Import docker-compose.yml
- Import containers: `docker compose up -d`

## SQL Dump
- Copy sql file to container: `docker cp directory_containing_sql_dump/2025-08-19_pg-faktencheck_dump.sql kibad-postgres:/2025-08-19_pg-faktencheck_dump.sql`
- Import sql file to database: `docker exec -it kibad-postgres psql -U postgres -d kibad -f /2025-08-19_pg-faktencheck_dump.sql`

## Access pgAdmin
- Go to: http://localhost:8080
- Click "Add new server"
    - General -> Name: "Postgres-Local"
    - Connection
        - Host name/address: "kibad-postgres"
        - Port: 5432
        - Username: "postgres"
        - Password: "kibad"
- Access tables: Servers -> Postgres-Local -> Databases -> kibad -> Schemas -> public -> Tables