# syntax=docker/dockerfile:1

## --- Base Builder Stage --- ##

FROM python:3.12-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.18@sha256:3adc3706091ce7c2fe595e669628caedd6d951551b92b258b7e7dbe06d9440bc /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=never


## --- Model Downloader Stage --- ##

FROM base AS models

WORKDIR /build

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system "huggingface_hub>=0.23"

COPY download_models.py /build

RUN python download_models.py && find /build/models -name ".cache" -type d -prune -exec rm -rf {} +

RUN test -f /build/models/musetalkV15/unet.pth && \
    test -f /build/models/sd-vae/diffusion_pytorch_model.safetensors && \
    test -f /build/models/whisper/config.json && \
    test -f /build/models/face-parse-bisent/79999_iter.pth && \
    test -f /build/models/s3fd/s3fd-619a316812.pth

## --- Deps Installer Stage --- ##
# Builds venv at /opt/venv with all dependencies and livewraith package

FROM base AS deps

RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project --no-editable

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

## --- Production Stage --- ##

FROM python:3.12-slim-trixie AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -r -u 1000 aiphish \
    && mkdir -p /aiphish/livewraith/avatars \
                /aiphish/livewraith/models \
                /aiphish/livewraith/db \
                /aiphish/livewraith/tempfiles \
    && chown -R aiphish:aiphish /aiphish/livewraith

ENV PATH="/opt/venv/bin:$PATH"
ENV S3FD_WEIGHTS="/aiphish/livewraith/models/s3fd/s3fd-619a316812.pth"

COPY --from=cloudflare/cloudflared:2026.9.1 /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY --from=models --chown=aiphish:aiphish /build/models /aiphish/livewraith/models
COPY --from=deps /opt/venv /opt/venv
COPY --chmod=755 start.sh /aiphish/livewraith/start.sh

WORKDIR /aiphish/livewraith

USER aiphish

CMD ["/aiphish/livewraith/start.sh"]
#CMD ["uvicorn", "aiphish.livewraith.main:app", "--port", "8080", "--host", "0.0.0.0", "--proxy-headers", "--forwarded-allow-ips=172.16.0.0/12"]
