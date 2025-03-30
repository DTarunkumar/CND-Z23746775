# Base image
FROM python:3.10-slim

# Working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# ✅ Copy your entire app source code including main.py and tests/
COPY . .

# ✅ Install pytest and run tests
RUN pip install pytest && pytest tests/

# Default port for Flask
ENV PORT=8080

# Start the app
CMD ["python", "main.py"]
