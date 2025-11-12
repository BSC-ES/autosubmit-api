#!/bin/bash

VENV_PATH=/home/autosubmit_user/autosubmit_venv

# Create a Python virtual environment named 'autosubmit_venv' in user home
python3 -m venv $VENV_PATH

# Install the autosubmit package in the virtual environment
$VENV_PATH/bin/pip install --upgrade pip
$VENV_PATH/bin/pip install autosubmit==4.1.14
