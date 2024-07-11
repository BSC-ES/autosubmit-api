# Dockerfile to test Autosubmit API in different Python versions

# Test Python 3.9
FROM python:3.9-slim-bullseye as test39

ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/
WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

RUN apt-get update && apt-get install -y git graphviz gcc lsof

# Install Autosubmit API 
ARG GIT_REF="main"
RUN git clone https://earth.bsc.es/gitlab/es/autosubmit-api.git . && \
    git checkout ${GIT_REF}
RUN pip install -e .[all]

RUN pytest

# Test Python 3.10
FROM python:3.10-slim-bullseye as test310

ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/
WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

RUN apt-get update && apt-get install -y git graphviz gcc lsof

COPY --from=test39 /app/autosubmit/ /app/autosubmit/

RUN pip install -e .[all]

RUN pytest

# Test Python 3.11
FROM python:3.11-slim-bullseye as test311

ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/
WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

RUN apt-get update && apt-get install -y git graphviz gcc lsof

COPY --from=test310 /app/autosubmit/ /app/autosubmit/

RUN pip install -e .[all]

RUN pytest

# Test Python 3.12
FROM python:3.12-slim-bullseye as test312

ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/
WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

RUN apt-get update && apt-get install -y git graphviz gcc lsof

COPY --from=test311 /app/autosubmit/ /app/autosubmit/

RUN pip install -e .[all]

RUN pytest