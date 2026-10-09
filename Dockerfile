FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY server/ /app/server/

EXPOSE 8080

CMD ["python", "server/control_plane.py"]
