FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN grep -v '^debugpy' requirements.txt > /tmp/requirements-prod.txt \
    && pip install --no-cache-dir -r /tmp/requirements-prod.txt \
    && rm /tmp/requirements-prod.txt

COPY . .

# collectstatic needs a minimal config.yaml (build-time only)
RUN printf 'SECRET_KEY: "build"\nDEBUG: false\nDBT_KEY: ""\nESV_KEY: ""\nDATABASES:\n  default:\n    ENGINE: django.db.backends.sqlite3\n    NAME: ":memory:"\n' > config.yaml \
    && python manage.py collectstatic --noinput \
    && rm config.yaml

ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "bible_research.wsgi:application"]
