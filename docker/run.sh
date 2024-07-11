#!/bin/bash

docker run --name autosubmit-api-container \
    --rm -d -p 8099:8000 \
    -v ~/autosubmit:/app/autosubmit/database \
    -v ~/autosubmit:/app/autosubmit/experiments \
    autosubmit-api