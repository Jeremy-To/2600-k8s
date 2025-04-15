FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y sudo procps iputils-ping && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash appuser && \
    echo "appuser ALL=(ALL) NOPASSWD: /usr/bin/python3" >> /etc/sudoers

COPY requirements.txt requirements.txt
COPY app.py app.py

RUN pip install --no-cache-dir -r requirements.txt

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["python3", "app.py"]
