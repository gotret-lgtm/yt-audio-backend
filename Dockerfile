# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install ffmpeg (required by yt-dlp)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5555 available to the world outside this container
EXPOSE 5555

# Define environment variable
ENV PORT 5555

# Run server.py when the container launches
CMD ["python", "server.py"]
