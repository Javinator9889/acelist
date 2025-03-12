# syntax=docker/dockerfile:1

ARG PYTHON_BASE_IMAGE=python
ARG PYTHON_VERSION=3.12
ARG RYE_URL=https://rye.astral.sh/get

FROM ${PYTHON_BASE_IMAGE}:${PYTHON_VERSION} AS rye

ARG RYE_URL

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# The virtual environment is created in the working directory where rye is run
# so the development and production environments must be in the same directory respectively.
WORKDIR /workspace

RUN \
  --mount=type=cache,target=/var/lib/apt/lists \
  --mount=type=cache,target=/var/cache/apt/archives \
  apt-get update \
  && apt-get install -y --no-install-recommends build-essential curl

ENV RYE_HOME="/opt/rye"
ENV PATH="$RYE_HOME/shims:$PATH"

# RYE_INSTALL_OPTION is required to build.
# See: https://github.com/mitsuhiko/rye/issues/246
RUN curl -sSf ${RYE_URL} | RYE_NO_AUTO_INSTALL=1 RYE_INSTALL_OPTION="--yes" bash

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a bind mount to some files to avoid having to copy them into
# into this layer.
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=requirements.lock,target=requirements.lock \
    --mount=type=bind,source=requirements-dev.lock,target=requirements-dev.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=src,target=src \
    rye sync --no-dev --no-lock && \
    rye build --wheel

# The final image is based on the slim Python image.
FROM ${PYTHON_BASE_IMAGE}:${PYTHON_VERSION}-slim AS acelist

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /wd

COPY --from=rye /workspace/dist /wd/dist

RUN pip install --no-cache-dir /wd/dist/*.whl
EXPOSE 8080

ENTRYPOINT [ "acelist" ]
