FROM python:3.11-slim
WORKDIR /app
# opencv-python-headless (Stage 9 color-histogram checks) still links against
# libglib2.0 at import time even without any GUI bindings — python:3.11-slim
# doesn't ship it, so the import fails without this.
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
