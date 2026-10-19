FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package*.json ./
RUN npm ci --ignore-scripts
COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src
RUN npm run build

FROM ubuntu:26.04 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib XDG_CACHE_HOME=/tmp/cache
ENV PATH="/opt/venv/bin:${PATH}"
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3.14 python3.14-venv libgl1 libglu1-mesa libxrender1 libxext6 libsm6 libgomp1 && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home app && python3.14 -m venv /opt/venv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY --from=frontend /build/dist ./dist
RUN mkdir -p .runtime artifacts && chown -R 10001:10001 .runtime artifacts
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --start-period=120s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4)"
CMD ["uvicorn","backend.app:app","--host","0.0.0.0","--port","8000","--workers","1"]
