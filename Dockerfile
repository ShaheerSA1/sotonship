# Nostobon server for Fly.io. The database lives on a volume at /data (NOSTOBON_DB in fly.toml),
# built from the committed data/ files on first boot by db.init.
FROM python:3.14-slim
WORKDIR /srv
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt
COPY app app
COPY data data
# one-off fixes run with fly ssh console
COPY scripts/classify_labels.py scripts/
EXPOSE 8000
# One process only: app/db.py shares one SQLite connection
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
