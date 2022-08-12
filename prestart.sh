#! /usr/bin/env bash

# Let the DB start
sleep 10
# Run migrations
# alembic upgrade head
# Init
python -m app.commands db-init