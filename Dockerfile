# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14
FROM node:24.22.1-bookworm-slim AS node
FROM python:${PYTHON_VERSION}-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Keep the existing development utilities available to users of this image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       gnupg \
       ca-certificates \
       build-essential \
       git \
       git-lfs \
    && rm -rf /var/lib/apt/lists/*

RUN git lfs install --system

# Use the patched official runtime for signature parity tooling.
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
RUN npm install -g transloadit

# Install Poetry so we match the GitHub Actions toolchain
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry==2.4.1

WORKDIR /workspace
