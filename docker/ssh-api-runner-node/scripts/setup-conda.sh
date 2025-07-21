#!/bin/bash

# Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
bash miniconda.sh -b -p /opt/miniconda
rm miniconda.sh
export PATH="/opt/miniconda/bin:$PATH"
conda init --all
conda tos accept

# Create conda environment
conda create -y -n autosubmit_env python=3.10

# Install autosubmit package
conda run -n autosubmit_env pip install autosubmit==4.1.14
