FROM python:3.11-slim

RUN apt update -y && \
    apt install libvips-dev -y

COPY main.py /app/
COPY requirements.txt /app/

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 9000
ENV CLIENT_MAX_SIZE=110000000

CMD python main.py
