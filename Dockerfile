# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
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
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (for Smart CDN parity tests) and supporting CLI tooling
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g transloadit \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry so we match the GitHub Actions toolchain
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry

WORKDIR /workspace
