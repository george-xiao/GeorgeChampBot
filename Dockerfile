FROM ubuntu:22.04 AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-dev python3-pip \
    ffmpeg python3-gdbm \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./requirements.txt ./
RUN pip3 install -r requirements.txt

# Copy test source files
FROM base AS test

COPY ./requirements-test.txt ./
RUN pip3 install -r requirements-test.txt

COPY ./pytest.ini ./
COPY ./tests ./tests
COPY ./commands ./commands
COPY ./common ./common
COPY ./components ./components

# Fallback default; run-tests.sh overrides this to forward "$@" to pytest.
CMD ["python3", "-m", "pytest", "-v"]


# Copy source files
FROM base AS prod

COPY ./.env ./
COPY ./GeorgeChampBot.py ./
COPY ./commands ./commands
COPY ./common ./common
COPY ./components ./components

# Run GeorgeChampBot
CMD ["python3", "./GeorgeChampBot.py"]
