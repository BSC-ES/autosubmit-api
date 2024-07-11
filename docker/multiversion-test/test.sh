#!/bin/bash

# Build the docker image and then remove it

docker build -t multiversion-test . && docker rmi multiversion-test