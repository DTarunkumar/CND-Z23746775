# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of your app
COPY . .

# Set environment variable for Flask to run
ENV PORT=8080

# Run the application
CMD ["python", "main.py"]
