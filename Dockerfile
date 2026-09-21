# syntax=docker/dockerfile:1

## --- Builder Stage --- ##

FROM python:3.12-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1

WORKDIR /build

COPY download_models.py /build
RUN uv pip install --system --no-cache-dir huggingface_hub>=0.23
RUN python download_models.py && find /build/models -name ".cache" -type d -prune -exec rm -rf {} +

RUN test -f /build/models/musetalkV15/unet.pth && \
    test -f /build/models/sd-vae/diffusion_pytorch_model.safetensors && \
    test -f /build/models/whisper/config.json && \
    test -f /build/models/face-parse-bisent/79999_iter.pth \
    test -f /build/models/s3fd/s3fd-619a316812.pth

RUN mkdir -p /wheelhouse

RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /build/livewraith/

WORKDIR /build/livewraith
RUN uv export --locked --no-dev --no-emit-workspace --no-editable --format requirements.txt > requirements.txt 
RUN pip wheel --wheel-dir /wheelhouse --extra-index-url https://download.pytorch.org/whl/cu121 -r requirements.txt

WORKDIR /build/livewraith
COPY . /build/livewraith/
RUN uv build --wheel && cp dist/*.whl /wheelhouse/

## --- Install Stage --- ##

FROM python:3.12-slim-trixie AS install

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1

COPY --from=builder /wheelhouse /wheelhouse

RUN uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python --no-index --find-links /wheelhouse aiphish-livewraith

RUN mkdir -p /aiphish/livewraith/avatars \
             /aiphish/livewraith/models \
             /aiphish/livewraith/db \
             /aiphish/livewraith/tempfiles

RUN useradd -r -u 1000 aiphish && chown -R aiphish:aiphish /aiphish/livewraith

## --- Production Stage --- ##

FROM python:3.12-slim-trixie AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=install /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

ENV S3FD_WEIGHTS="/aiphish/livewraith/models/s3fd/s3fd-619a316812.pth"

COPY --from=install /aiphish /aiphish

RUN useradd -r -u 1000 aiphish

COPY --from=builder /build/models /aiphish/livewraith/models

WORKDIR /aiphish/livewraith

USER aiphish

CMD ["uvicorn", "aiphish.livewraith.main:app", "--port", "8080", "--host", "0.0.0.0", "--proxy-headers", "--forwarded-allow-ips=172.16.0.0/12"]

