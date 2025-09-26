## setup

### python
install required packages:
- python-dotenv
- psycopg2

### environment
create a .env file with the credentials set in the docker compose:
```
DB_USER=<username-here>
DB_PASSWORD=<password-here>
```

## running

from the scripts directory run `python db_converter.py`
