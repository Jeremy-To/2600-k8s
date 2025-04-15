FROM ubuntu:20.04

RUN apt-get update && apt-get install -y openssh-server sudo && \
    rm -rf /var/lib/apt/lists/*

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

RUN echo 'root:password123' | chpasswd

RUN mkdir -p /run/sshd

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
