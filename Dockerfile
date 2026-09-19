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
    test -f /build/models/face-parse-bisent/79999_iter.pth

RUN mkdir -p /wheelhouse

COPY pyproject.toml uv.lock /build/livewraith/

WORKDIR /build/livewraith
RUN uv export --locked --no-dev --no-emit-workspace --no-editable --format requirements.txt > requirements.txt 
RUN pip wheel --wheel-dir /wheelhouse --extra-index-url https://download.pytorch.org/whl/cu121 -r requirements.txt

WORKDIR /build/livewraith
COPY . /build/livewraith/
RUN uv build --wheel && cp dist/*.whl /wheelhouse/

## --- Production Stage --- ##

FROM python:3.12-slim-trixie AS production

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1

COPY --from=builder /wheelhouse /wheelhouse

RUN uv pip install --system --no-index --find-links /wheelhouse aiphish-livewraith

RUN mkdir -p /aiphish/livewraith/avatars

RUN mkdir -p /aiphish/livewraith/models

COPY --from=builder /build/models /aiphish/livewraith/models

RUN mkdir -p /aiphish/livewraith/db

RUN mkdir -p /aiphish/livewraith/tempfiles

WORKDIR /aiphish/livewraith

CMD ["uvicorn", "aiphish.livewraith.main:app", "--port", "80", "--host", "0.0.0.0", "--proxy-headers", "--forwarded-allow-ips=172.16.0.0/12"]

