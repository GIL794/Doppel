# One image, one origin: builds the React app and serves it from the FastAPI
# backend, so cookies and /api need no cross-site settings.
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV REACT_APP_BACKEND_URL=""
RUN npx craco build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/build /app/frontend-dist
ENV APP_ENV=production FRONTEND_DIST=/app/frontend-dist PORT=10000
EXPOSE 10000
CMD ["python", "server.py"]
