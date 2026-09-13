# syntax=docker/dockerfile:1

## --- Builder Stage --- ##

FROM python:3.13-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1

WORKDIR /build

RUN mkdir -p /wheelhouse

COPY livewraith/pyproject.toml livewraith/uv.lock /build/livewraith/

WORKDIR /build/livewraith
RUN uv export --locked --no-dev --no-emit-workspace --no-editable --format requirements.txt > requirements.txt 
RUN pip wheel --wheel-dir /wheelhouse -r requirements.txt


WORKDIR /build/livewraith
COPY livewraith/ /build/livewraith/
RUN uv build --wheel && cp dist/*.whl /wheelhouse/


## --- Production Stage --- ##

FROM python:3.13-slim-trixie AS production


COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1

COPY --from=builder /wheelhouse /wheelhouse

RUN uv pip install --system --no-index --find-links /wheelhouse aiphish-livewraith

WORKDIR /aiphish

CMD ["uvicorn", "aiphish.livewraith.main:app", "--port", "80", "--host", "0.0.0.0", "--proxy-headers", "--forwarded-allow-ips=172.16.0.0/12"]

