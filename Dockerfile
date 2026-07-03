# Pinned by digest for reproducible builds. To update: pull the new
# python:3.12-slim, read `docker inspect --format '{{index .RepoDigests 0}}'`,
# and replace the digest below.
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME ["/data"]

EXPOSE 8080

ENV DB_PATH=/data/rcdb.db

# Report container health from the app's own probe (no extra tooling needed).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4).status==200 else 1)"]

CMD ["python", "app.py"]
