# pod1-webapp-src/Dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install sudo and create a non-root user
RUN apt-get update && apt-get install -y sudo procps iputils-ping && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash appuser && \
    # Allow appuser to run python3 with sudo without password
    echo "appuser ALL=(ALL) NOPASSWD: /usr/bin/python3" >> /etc/sudoers

# Copy application files
COPY requirements.txt requirements.txt
COPY app.py app.py
# Utility script will be created by app.py if needed, but let's ensure permissions
# RUN touch utility.py && chown appuser:appuser utility.py

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose port
EXPOSE 8080

# Command to run the application
CMD ["python3", "app.py"]
