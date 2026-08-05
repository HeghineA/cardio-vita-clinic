FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin appuser
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV HOST=0.0.0.0
ENV PORT=8080
RUN mkdir -p /app/data /app/backups \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
CMD ["python", "server.py"]
