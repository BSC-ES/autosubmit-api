FROM python:3.8-slim-bullseye

# Set the environment
ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/

WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

RUN apt-get update && apt-get install -y git graphviz

# Install Autosubmit API 
# If GIT_REF is set, it will install from the specified branch/tag/commit. 
# Otherwise, if AUTOSUBMIT_VERSION is set, it will install the specified version from pypi.
# Otherwise, it will install the latest version from pypi.
ARG GIT_REF
ARG AUTOSUBMIT_VERSION
RUN if [ -n "${GIT_REF}" ] ; then \
      pip3 install git+https://earth.bsc.es/gitlab/es/autosubmit-api.git@${GIT_REF}; \
    elif [ -n "${AUTOSUBMIT_VERSION}" ] ; then \
      pip3 install autosubmit-api==${AUTOSUBMIT_VERSION}; \
    else \
      pip3 install autosubmit-api; \
    fi

COPY autosubmitrc /app/configs/autosubmitrc

# Setup API env vars
ENV PROTECTION_LEVEL=ALL
ENV JWT_SECRET="k87;Zg,o5?MSC(/@#-LbzgE3PH-5ki.ZvS}N.s09v>I#v8I'00THrA-:ykh3HX?"

ENV CAS_LOGIN_URL=""
ENV CAS_VERIFY_URL=""

ENV GITHUB_OAUTH_CLIENT_ID=""
ENV GITHUB_OAUTH_CLIENT_SECRET=""
ENV GITHUB_OAUTH_WHITELIST_ORGANIZATION=""
ENV GITHUB_OAUTH_WHITELIST_TEAM=""

ENV AUTOSUBMIT_CONFIGURATION="/app/configs/autosubmitrc"

# Entrypoint
ENTRYPOINT ["autosubmit_api"]
CMD ["start", "-b=0.0.0.0:8000", "--log-file=api.log"]
