FROM ubuntu:22.04 AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-dev python3-pip \
    ffmpeg python3-gdbm \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from uv.lock into a venv built on the system python3
# (system python is required: shelve needs python3-gdbm from apt)
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"
COPY ./pyproject.toml ./uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy test source files
FROM base AS test

RUN uv sync --frozen --no-install-project --group test

COPY ./GeorgeChampBot.py ./
COPY ./common ./common
COPY ./commands ./commands
COPY ./components ./components
COPY ./tests ./tests

# Fallback default; run-tests.sh overrides this to forward "$@" to pytest.
CMD ["python3", "-m", "pytest", "-v"]


# Copy source files
FROM base AS prod

COPY ./.env ./
COPY ./GeorgeChampBot.py ./
COPY ./common ./common
COPY ./commands ./commands
COPY ./components ./components

# Run GeorgeChampBot
CMD ["python3", "./GeorgeChampBot.py"]
