FROM python:3.12-alpine

LABEL maintainer="fahmula"

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt && \
    chmod +x /app/entrypoint.sh

COPY . /app/

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
