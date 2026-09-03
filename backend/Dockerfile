# Python 3.13.15 slim
FROM python:3.13.15-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a AS runtime-base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.in requirements.lock ./
RUN python -m pip install --disable-pip-version-check --require-hashes \
    --retries 10 --timeout 60 -r requirements.lock

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime-base AS quality

COPY requirements-dev.in requirements-dev.lock ./
RUN python -m pip install --disable-pip-version-check --require-hashes \
    --retries 10 --timeout 60 -r requirements-dev.lock

COPY pytest.ini ./
COPY pyproject.toml ./
COPY pip-audit-exceptions.toml ./
COPY performance ./performance
COPY quality ./quality
COPY scripts ./scripts
COPY tests ./tests

FROM runtime-base AS runtime
