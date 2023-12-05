FROM python:3.7.17-slim-bullseye

ARG AUTOSUBMIT_ROOT_DIR=/app/autosubmit/

ARG API_VERSION=4.0.0b2

WORKDIR "${AUTOSUBMIT_ROOT_DIR}"

COPY autosubmitrc /etc/

RUN pip3 install autosubmit-api==${API_VERSION}

# Setup API env vars
ENV PROTECTION_LEVEL=ALL
ENV JWT_SECRET="M87;Z$,o5?MSC(/@#-LbzgE3PH-5ki.ZvS}N.s09v>I#v8I'00THrA-:ykh3HX?"
ENV CAS_LOGIN_URL=""
ENV CAS_VERIFY_URL=""

ENTRYPOINT ["autosubmit_api"]
CMD ["start", "-b=0.0.0.0:8000", "--log-file=api.log"]
