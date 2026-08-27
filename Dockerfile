FROM python:3.11-slim@sha256:9c900dea9e8fb7e16277c179b555cc72d29a352dbc33cff48ad5a0412fd5bfc7 AS builder

ARG AIPG_VALIDATOR_RELEASE_TAG=""

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN python -m pip install --no-cache-dir uv==0.12.5

COPY pyproject.toml uv.lock README.md ./
COPY validator/ validator/
COPY scripts/stamp-release-tag.py scripts/stamp-release-tag.py

RUN python scripts/stamp-release-tag.py "$AIPG_VALIDATOR_RELEASE_TAG" \
    && uv sync --frozen --no-dev --no-editable --extra media \
    && rm -rf /root/.cache/uv

FROM python:3.11-slim@sha256:9c900dea9e8fb7e16277c179b555cc72d29a352dbc33cff48ad5a0412fd5bfc7 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VALIDATOR_ENV=/app/.env \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

COPY --from=builder /app /app

RUN useradd --create-home --shell /bin/sh validator \
    && chown -R validator:validator /app

USER validator

EXPOSE 8790

ENTRYPOINT ["aipg-validator"]
CMD ["run"]
