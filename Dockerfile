FROM python:3.11-slim

ENV HOST=0.0.0.0
ENV PORT=9000
ENV URL_LOCATION=/upload/
ENV UPLOAD_CALLBACK=
ENV UPLOAD_DIRECTORY=/uploads
ENV GEN_HOST=dekralk.amzs.si
ENV GEN_SCHEME=https

RUN apt update -y && \
    apt install libvips-dev -y

COPY main.py /app/
COPY requirements.txt /app/

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 9000
ENV CLIENT_MAX_SIZE=110000000

CMD python main.py --host $HOST --port $PORT --url $URL_LOCATION --callback $UPLOAD_CALLBACK --dir $UPLOAD_DIRECTORY --gen-host $GEN_HOST --gen-scheme $GEN_SCHEME --client-max-size $CLIENT_MAX_SIZE
