#!/bin/sh

sleep 5

export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root-token'

vault kv put secret/postgres \
    db=reviews_db \
    user=postgres \
    password=postgres123 \
    host=db \
    port=5432

echo "Secrets initialized!"