#!/bin/bash

# Start the SSH service (using sudo since we're running as non-root user)
sudo service ssh start

# Keep the container running
tail -f /dev/null