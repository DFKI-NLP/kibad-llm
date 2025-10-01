# Title

TODO: add description and title

## Set up Podman (Preferred)

Installation instructions for the [podman project](https://podman.io/) are provided below.

<ul>
    <li>
        <details>
            <summary>Linux: Install <a href="https://docs.podman.io/en/stable/markdown/podman.1.html">podman</a> and <a href="https://docs.podman.io/en/stable/markdown/podman-compose.1.html">podman-compose</a> with your package manager of choice. (for debian based distros: <code>sudo apt install podman podman-compose</code>)</summary>
            podman and podman-compose are available as native packages in many distributions, like debian: <a href="https://packages.debian.org/trixie/podman">podman</a> <a href="https://packages.debian.org/trixie/podman-compose">podman-compose</a>
        </details>
    </li>
    <ul>
        <li>
            <details>
                <summary>If you have installed docker, set the compose provider for podman: <code>export PODMAN_COMPOSE_PROVIDER=podman-compose</code></summary>
                As stated in its <a href="https://docs.podman.io/en/stable/markdown/podman-compose.1.html">manpage<a>, <q>podman compose is a thin wrapper around an external compose provider such as docker-compose or podman-compose.</q>. docker-compose takes precedence, but we want to use podman-compose. Changing the podman compose provider only changes which provider podman compose uses and does not change how docker works in any way.
            </details>
        </li>
        <li>
            <details>
                <summary>In case your distro has no configured registries, adding docker.io gets you going: <code>echo 'unqualified-search-registries = ["docker.io"]' | sudo tee -a /etc/containers/registries.conf</code></summary>
                Registries contain already built containers. Anyone can host a registry and so Fedora ships with three different registries per default:
                <ol>
                    <li>docker.io</li>
                    <li>registry.fedoraproject.org</li>
                    <li>registry.access.redhat.com</li>
                </ol>
                Whilst docker.io is the most widely known registry, since it is dockers default, it makes sense to maintain independent structures. Hencewhy redhat and fedora provide their own registries.<br>
                If you know what you're doing, you can set your own choice of registry. Otherwise we recommend docker.io because it has proven to work in our testing.<br>
                In case your distro does not preconfigure registries, like on debian based distros, podman will let you know it needs a registry by throwing an error.
            </details>
        </li>
    </ul>
    <li>
        <details>
            <summary>MacOS: To install podman on macos run <code>brew install podman podman-compose</code> then run <code>podman machine init</code> and <code>podman machine start</code> to complete setup.</summary>
            This starts a very small Linux VM that you can stop with <code>podman machine stop</code>. You do not need any further setup commands as we neither need root nor the docker api.
        </details>
    </li>
</ul>

## Alternative: set up Docker (not recommended)

Using docker requires the docker daemon to run. Said daemon needs to run as root and consumes resources, whilst podman neither needs a daemon, to run as root, greatly reducing the attack vector. If we were to assume that this project was only deployed on reasonably powerful machines (which is a false assumption), there would still be the issue that the docker daemon running as root is a major point for exploitation. Just last month docker has received two CVEs rated critical ([CVE-2025-7390](https://www.cve.org/CVERecord?id=CVE-2025-7390), [CVE-2025-9074](https://www.cve.org/CVERecord?id=CVE-2025-9074)).

Therefore its resource and security reasons that make us recommend podman over docker.

If however you still want or need to install docker, you can find information on how to do so on ubuntu below.

- Ubuntu: Follow instructions here: https://docs.docker.com/engine/install/ubuntu/ and https://docs.docker.com/engine/install/linux-postinstall/

## Start containers with docker-compose.yml

- Podman: `podman compose up -d`
- Docker (not recommended): `docker compose up -d`

### SQL Dump

Please make sure to wait a few seconds for all containers to start fully before trying to load the database.

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

- Podman: `podman compose down`
- Docker: `docker compose down`

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
