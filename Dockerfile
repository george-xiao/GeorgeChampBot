FROM ubuntu:22.04

# Install Python + dependencies 
RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip
RUN apt-get install -y ffmpeg
RUN apt-get install -y python3-gdbm

# Install Python dependencies
COPY ./requirements.txt ./
RUN pip3 install -r requirements.txt

# Copy source files
COPY ./.env ./
COPY ./GeorgeChampBot.py ./
COPY ./common ./common
COPY ./components ./components

# Copy cookies file
COPY ./cookies.txt ./cookies.txt


# Run GeorgeChampBot
CMD ["python3", "./GeorgeChampBot.py"]
