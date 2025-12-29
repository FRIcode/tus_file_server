FROM python:3.13-slim

RUN apt update -y && \
    apt install libvips-dev ffmpeg -y

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .

EXPOSE 9000
ENV CLIENT_MAX_SIZE=110000000
ENV UPLOAD_DIRECTORY=/uploads
ENV HOST=0.0.0.0

CMD python main.py
