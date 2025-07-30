# Use a specific lightweight base image
FROM python:3-alpine

# Combine related APK commands to reduce image layers and cleanup cache
RUN apk update && apk upgrade && apk add --no-cache \
    postgresql-client \
    util-linux \
    bash && \
    python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir gunicorn

# Create a non-root user for security
RUN addgroup -S pgassistant && adduser -S pgassistant -G pgassistant -h /home/pgassistant
USER pgassistant

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    DEBUG=False \
    PATH="/home/pgassistant/venv/bin:$PATH"

WORKDIR /home/pgassistant

# Create and activate virtual environment in one step
RUN python -m venv /home/pgassistant/venv

# Copy requirements and install dependencies
COPY --chown=pgassistant:pgassistant requirements.txt /home/pgassistant/requirements.txt
RUN pip install --no-cache-dir -r /home/pgassistant/requirements.txt

# Copy application files in a single command to reduce layers
COPY --chown=pgassistant:pgassistant . /home/pgassistant/
RUN rm -rf media

# Expose application port
EXPOSE 5085

# Define entry point for the application
ENTRYPOINT ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]