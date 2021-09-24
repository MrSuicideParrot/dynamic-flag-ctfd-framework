FROM python:3

COPY requirements.txt /app
COPY . /app

ENTRYPOINT python /app/main.py