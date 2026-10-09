FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/omni
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home --uid 10001 omni
COPY app ./app
USER omni
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--no-access-log","--no-proxy-headers"]
FROM base AS renderer
USER root
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
RUN playwright install --with-deps chromium && chmod -R a+rX /opt/browsers
USER omni
CMD ["uvicorn","app.renderer:app","--host","0.0.0.0","--port","8001","--no-access-log","--no-proxy-headers"]
