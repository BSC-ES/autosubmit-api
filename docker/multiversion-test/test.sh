#!/bin/bash

# Build the docker image and then remove it

docker build --no-cache -t multiversion-test . && docker rmi multiversion-test