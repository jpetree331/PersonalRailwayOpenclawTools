# TOOLS — OpenClaw tool backends (Drive Playground + more later)
# Deploy to Railway; OpenClaw calls this service via its public URL.

FROM python:3.12-slim

WORKDIR /app

# Drive Playground service
COPY drive_playground/ ./drive_playground/
RUN pip install --no-cache-dir -r drive_playground/requirements.txt

# Railway sets PORT; default for local
ENV PORT=8765
EXPOSE 8765

WORKDIR /app/drive_playground
CMD ["sh", "-c", "exec python3 -m uvicorn drive_playground_service:app --host 0.0.0.0 --port ${PORT}"]
