#!/bin/bash

docker build -t autosubmit-api --progress=plain . &> build.log
