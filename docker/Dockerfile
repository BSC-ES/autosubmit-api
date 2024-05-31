FROM python:3.8-slim-bullseye

# Default API version
ARG API_VERSION=4.0.0b8

# Set the environment
ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/

WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

COPY autosubmitrc /etc/

RUN apt-get update && apt-get install -y git graphviz

RUN pip3 install autosubmit-api==${API_VERSION}

# Setup API env vars
ENV PROTECTION_LEVEL=ALL
ENV JWT_SECRET="k87;Zg,o5?MSC(/@#-LbzgE3PH-5ki.ZvS}N.s09v>I#v8I'00THrA-:ykh3HX?"

ENV CAS_LOGIN_URL=""
ENV CAS_VERIFY_URL=""

ENV RUN_BACKGROUND_TASKS_ON_START="False"
ENV DISABLE_BACKGROUND_TASKS="False"

ENV GITHUB_OAUTH_CLIENT_ID=""
ENV GITHUB_OAUTH_CLIENT_SECRET=""
ENV GITHUB_OAUTH_WHITELIST_ORGANIZATION=""
ENV GITHUB_OAUTH_WHITELIST_TEAM=""

# Entrypoint
ENTRYPOINT ["autosubmit_api"]
CMD ["start", "-b=0.0.0.0:8000", "--log-file=api.log"]
