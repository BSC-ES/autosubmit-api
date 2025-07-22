FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    openssh-server \
    wget \
    python3-venv \
    sudo \
    && apt-get clean

# Create a non-root user
RUN useradd -m -s /bin/bash autosubmit_user && \
    echo 'autosubmit_user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Make /bin/bash the default shell for autosubmit_user
RUN chsh -s /bin/bash autosubmit_user

# Copy script files to the container
COPY scripts/ /usr/local/bin/

# Make scripts executable and set ownership
RUN chmod +x /usr/local/bin/*.sh && \
    chown -R autosubmit_user:autosubmit_user /usr/local/bin/*.sh

# Change to autosubmit_user for the rest of the Dockerfile
USER autosubmit_user

# Create authorized_keys directory with an empty authorized_keys file for the autosubmit_user user
RUN mkdir -p /home/autosubmit_user/.ssh && \
    chmod 700 /home/autosubmit_user/.ssh && \
    touch /home/autosubmit_user/.ssh/authorized_keys && \
    chmod 600 /home/autosubmit_user/.ssh/authorized_keys

# Run installation scripts
RUN /usr/local/bin/setup-conda.sh && \
    /usr/local/bin/setup-venv.sh

# Expose SSH port
EXPOSE 22

# Start SSH service
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]