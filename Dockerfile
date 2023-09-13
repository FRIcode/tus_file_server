FROM python:3.11-slim

RUN apt update -y && \
    apt install libvips-dev -y

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .

EXPOSE 9000
ENV CLIENT_MAX_SIZE=110000000

CMD python main.py
