# Dockerfile for Breadbox's backend
# 
# Remember to mount the following:
#   /config    | Config file, SSL certificate, and user database.
#   /archives  | Main archive

FROM python:3.12

WORKDIR /app

COPY breadbox ./breadbox
COPY routers ./routers
COPY main.py .
COPY users.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

ENV BREADBOX_CONFIG="/config"

EXPOSE 80/tcp

ENTRYPOINT ["python", "main.py"]
