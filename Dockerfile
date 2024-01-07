# Use the official Python image
FROM python:3.11-slim-bookworm

LABEL maintainer="fahmula"

# Set the working directory in the container
WORKDIR /app

# Install curl and ping
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl iputils-ping && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app/

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Define the command to run your Python script
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:app"]