- Local db setup:
    - `docker run --name tests-1 -p 5436:5432 -e POSTGRES_PASSWORD=password postgres`
    - `createdb -h localhost -p 5436 -U postgres tests-1`
    - `pg_restore -h localhost -p 5436 -U postgres -d tests-1 -v --no-owner --clean "db_backups/backup_20251103_085732.dump"`
- Add DBT client:
    - `cd bible/services`
```
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH" && openapi-generator generate -i dbt_openapi.json -g python -o dbt_client --skip-validate-spec
```
- `db_backups/local_db_backup.sh`
  - Runs a local db backup
- Command `python manage.py import_esv_verses` on local machine took
    - For local SQLite: 0:02:52.066889
    - For remote free Aiven PostgreSQL: 0:46:01.924594

