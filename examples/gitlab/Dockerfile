# syntax=docker/dockerfile:1

# The only place where the image pins uv. Dependabot (GitHub) bumps this line;
# keep UV_VERSION in the CI config in sync with it.
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv


################################
# BUILDER
# Installs the locked runtime dependencies and the project itself
# (a regular, non-editable package) into /app/.venv
################################
FROM python:3.14-slim-trixie AS builder

COPY --from=uv /uv /uvx /bin/

# Compile bytecode at install time, copy files out of the cache mount and
# never download a Python: the image's interpreter is the one in production.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first: this layer is rebuilt only when uv.lock or pyproject.toml change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# The build context is limited by .dockerignore (allowlist).
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable


################################
# DEVELOPMENT
# Used by docker compose: all dependency groups, the project installed in
# editable mode, sources bind-mounted from the host. Runs as root so that the
# container can write into the bind mount whatever the host UID is.
################################
FROM python:3.14-slim-trixie AS development

COPY --from=uv /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

CMD ["python", "-m", "example_app"]


################################
# PRODUCTION
# Final image: Python and the virtual environment only, no uv, no sources
################################
FROM python:3.14-slim-trixie AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH" \
    LOG_FORMAT=json

# A fixed numeric UID/GID, so that `runAsNonRoot` and volume permissions
# work the same everywhere.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

# Owned by root: the application cannot modify its own code and dependencies.
COPY --from=builder /app/.venv /app/.venv

WORKDIR /app
USER 10001:10001

CMD ["python", "-m", "example_app"]
