FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VALIDATOR_ENV=/app/.env

WORKDIR /app

COPY pyproject.toml README.md ./
COPY validator/ validator/

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN useradd --create-home --shell /bin/sh validator \
    && chown -R validator:validator /app

USER validator

EXPOSE 8790

ENTRYPOINT ["aipg-validator"]
CMD ["run"]
