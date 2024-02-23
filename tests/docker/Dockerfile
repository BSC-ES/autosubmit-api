FROM python:3.8-slim-bullseye

WORKDIR /

RUN apt-get update && apt-get install -y git graphviz

RUN git clone https://earth.bsc.es/gitlab/es/autosubmit_api.git

WORKDIR /autosubmit_api/

RUN git checkout v4.0.0b4

RUN pip install .

RUN pip install -U pytest pytest-cov

RUN pytest --cov=autosubmit_api --cov-config=.coveragerc --cov-report=html tests/