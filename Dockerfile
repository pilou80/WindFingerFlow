FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends libcairo2 fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.10 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data
COPY fonts ./fonts
RUN uv sync --frozen --no-dev && chmod -R a+rX /app
ARG GIT_SHA=unknown
RUN useradd --create-home app && mkdir -p /work && chown app /work
USER app
ENV WFF_WORKDIR=/work PATH="/app/.venv/bin:$PATH" WFF_GIT_SHA=$GIT_SHA
EXPOSE 8000
CMD ["uvicorn", "windfingerflow.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
