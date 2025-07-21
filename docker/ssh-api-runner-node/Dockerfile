FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    openssh-server \
    wget \
    python3-venv \
    && apt-get clean

# Create authorized_keys directory with an empty authorized_keys file
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh && touch /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys

# Create conda environment and install autosubmit
COPY scripts/setup-conda.sh /usr/local/bin/setup-conda.sh
RUN chmod +x /usr/local/bin/setup-conda.sh && /usr/local/bin/setup-conda.sh

# Create Python virtual environment and install autosubmit
COPY scripts/setup-venv.sh /usr/local/bin/setup-venv.sh
RUN chmod +x /usr/local/bin/setup-venv.sh && /usr/local/bin/setup-venv.sh

# Copy entrypoint script
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose SSH port
EXPOSE 22

# Start SSH service
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]