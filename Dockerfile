# ResearchLedger service image. The index is built by the deploy workflow (ingest + embed at the pinned commit)
# and copied in, so an image is one corpus at one commit and needs no storage at runtime.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY researchledger ./researchledger
RUN pip install ".[service]" && useradd --uid 10001 --no-create-home app

ARG INDEX=.cache/index/marin.sqlite
COPY --chown=app ${INDEX} /app/index/marin.sqlite
ENV RL_INDEX=/app/index/marin.sqlite

USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn researchledger.service:app --host 0.0.0.0 --port ${PORT:-8080}"]
