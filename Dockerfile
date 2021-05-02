FROM python:3.9-slim

ENV HOST=0.0.0.0
ENV PORT=9000
ENV URL_LOCATION=/upload/
ENV UPLOAD_CALLBACK=
ENV UPLOAD_DIRECTORY=/uploads

COPY main.py /app/
COPY requirements.txt /app/

WORKDIR /app

RUN pip install -r requirements.txt

CMD python main.py --host $HOST --port $PORT --url $URL_LOCATION --callback $UPLOAD_CALLBACK --dir $UPLOAD_DIRECTORY
