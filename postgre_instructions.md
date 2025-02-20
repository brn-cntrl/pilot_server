## Installation (Mac)
brew install postgresql
pip install psycopg2 flask-sqlalchemy

### Start:
brew services start postgresql

### Stop:
brew services stop postgresql

### Restart:
brew services restart postgresql

### Setting up:
sudo mkdir -p /usr/local/var/postgres
sudo chown $(whoami) /usr/local/var/postgres
initdb /usr/local/var/postgres

### Create a user
createuser -s postgres

If permission error try:
sudo -u _postgres createuser -s postgres

### Check status:
pg_ctl -D /usr/local/var/postgres status

### Log in:
psql -U postgres

### Create database:
CREATE DATABASE exp_server_db;

### Check if DB is present:
\l

### Quit postgres:
\q

