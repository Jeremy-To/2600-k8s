# pod2-ssh-server-src/Dockerfile
FROM ubuntu:20.04

# Install OpenSSH server and sudo (useful for potential commands later)
RUN apt-get update && apt-get install -y openssh-server sudo && \
    rm -rf /var/lib/apt/lists/*

# Permit root login with password
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
# Allow password authentication
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
# For newer SSH versions, you might need this too (depends on base image)
# RUN echo 'UsePAM yes' >> /etc/ssh/sshd_config

# Set a weak password for root (e.g., "password123")
RUN echo 'root:password123' | chpasswd

# Create SSH host keys if they don't exist
RUN mkdir -p /run/sshd

# Expose SSH port
EXPOSE 22

# Command to run sshd in the foreground
CMD ["/usr/sbin/sshd", "-D"]
