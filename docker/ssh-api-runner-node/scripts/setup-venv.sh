#!/bin/bash

VENV_PATH=/opt/autosubmit_venv

# Create a Python virtual environment named 'autosubmit_venv'
python3 -m venv $VENV_PATH

# Install the autosubmit package in the virtual environment
$VENV_PATH/bin/pip install --upgrade pip
$VENV_PATH/bin/pip install autosubmit==4.1.14
