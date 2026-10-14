FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

RUN groupadd -g 10001 serpent && \
    useradd -u 10001 -g serpent -m -s /bin/sh serpent

COPY VERSION /app/VERSION
COPY server/ /app/server/
RUN chown -R serpent:serpent /app

USER serpent

EXPOSE 8080

CMD ["python", "server/control_plane.py"]
