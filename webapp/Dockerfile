FROM python:3.10-slim
RUN apt update && apt install -y sudo iputils-ping iproute2 net-tools dnsutils ssh
RUN useradd -m exploit && echo 'exploit ALL=(ALL) NOPASSWD:/usr/local/bin/python3' >> /etc/sudoers
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
USER exploit
CMD ["python3", "app.py"]
