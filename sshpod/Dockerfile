FROM ubuntu:22.04

# Mise à jour + installation curl et dépendances
RUN apt-get update && apt-get install -y \
    curl \
    openssh-server \
    sudo \
    python3

# Configuration SSH
RUN mkdir /var/run/sshd

# Modification de la config SSH pour autoriser root
RUN sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Entrypoint pour changer le mdp de root via SECRET
CMD ["/entrypoint.sh"]
