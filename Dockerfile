FROM ubuntu:latest

# Install Python + dependencies 
RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip
RUN apt-get install -y ffmpeg

# Copy source files
COPY ./.env ./
COPY ./GeorgeChampBot.py ./
COPY ./common ./common
COPY ./components ./components
COPY ./requirements.txt ./

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Run GeorgeChampBot
CMD ["python3", "./GeorgeChampBot.py"]