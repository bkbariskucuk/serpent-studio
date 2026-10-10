FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    SERPENT_CONTROL_PLANE_DB=/var/lib/serpent/control_plane.db

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt \
    && useradd --system --uid 10001 --create-home serpent \
    && mkdir -p /var/lib/serpent \
    && chown serpent:serpent /var/lib/serpent
COPY --chown=serpent:serpent server/*.py /app/server/

USER serpent

EXPOSE 8080

CMD ["python", "server/control_plane.py"]
