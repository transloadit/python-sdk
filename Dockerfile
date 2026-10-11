# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

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

# Install Node.js 24 (for Smart CDN parity tests) and supporting CLI tooling
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g transloadit \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry so we match the GitHub Actions toolchain
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry==2.4.1

WORKDIR /workspace
