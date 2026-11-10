# Builds the web app, runs both test suites, then serves the API and the built web app.
FROM node:24.22.1-bookworm-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm test && npm run build

FROM python:3.12.8-slim-bookworm
WORKDIR /service
COPY service/requirements.txt service/requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt
COPY service/ ./
COPY mock-idp/ /mock-idp/
RUN python -m pytest -q && rm -f test-team-insights.db
COPY --from=web /web/dist ./static
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
