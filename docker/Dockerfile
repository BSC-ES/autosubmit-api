# Use build argument for Python version
ARG PYTHON_VERSION=3.9-slim-bullseye
FROM python:${PYTHON_VERSION}

# Set the environment
ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/

WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

RUN apt-get update && apt-get install -y git graphviz gcc lsof && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Install Autosubmit API 
# If GIT_REF is set, it will install from the specified branch/tag/commit. 
# Otherwise, if AUTOSUBMIT_VERSION is set, it will install the specified version from pypi.
# Otherwise, it will install the latest version from pypi.
ARG GIT_REF
ARG AUTOSUBMIT_VERSION
RUN if [ -n "${GIT_REF}" ] ; then \
      pip3 install --no-cache-dir git+https://github.com/BSC-ES/autosubmit-api.git@${GIT_REF}; \
    elif [ -n "${AUTOSUBMIT_VERSION}" ] ; then \
      pip3 install --no-cache-dir autosubmit-api==${AUTOSUBMIT_VERSION}; \
    else \
      pip3 install --no-cache-dir autosubmit-api; \
    fi

COPY autosubmitrc /app/configs/autosubmitrc

# Setup API env vars
ENV AS_API_ROOT_PATH=""
ENV PROTECTION_LEVEL=ALL
ENV JWT_SECRET="k87;Zg,o5?MSC(/@#-LbzgE3PH-5ki.ZvS}N.s09v>I#v8I'00THrA-:ykh3HX?"

ENV CAS_LOGIN_URL=""
ENV CAS_VERIFY_URL=""

ENV GITHUB_OAUTH_CLIENT_ID=""
ENV GITHUB_OAUTH_CLIENT_SECRET=""
ENV GITHUB_OAUTH_WHITELIST_ORGANIZATION=""
ENV GITHUB_OAUTH_WHITELIST_TEAM=""

ENV AUTOSUBMIT_CONFIGURATION="/app/configs/autosubmitrc"

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Change ownership of the working directory
RUN chown -R appuser:appgroup "${AUTOSUBMIT_ROOT_DIR}"

# Switch to the non-root user
USER appuser

# Entrypoint
ENTRYPOINT ["autosubmit_api"]
CMD ["start", "-b=0.0.0.0:8000", "--log-file=api.log"]
