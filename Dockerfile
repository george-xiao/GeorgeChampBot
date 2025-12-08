FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-dev python3-pip \
    ffmpeg python3-gdbm \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./requirements.txt ./
RUN pip3 install -r requirements.txt

# Copy source files
COPY ./.env ./
COPY ./GeorgeChampBot.py ./
COPY ./common ./common
COPY ./components ./components

# Run GeorgeChampBot
CMD ["python3", "./GeorgeChampBot.py"]
