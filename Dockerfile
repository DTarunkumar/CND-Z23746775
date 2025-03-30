# Base image
FROM python:3.10-slim

# Working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# ✅ Copy your entire app source code including main.py and tests/
COPY . .

# ✅ Set PYTHONPATH so `main` is visible
ENV PYTHONPATH="${PYTHONPATH}:/app"
# ✅ Install pytest and run tests
RUN pip install pytest && pytest tests/

# Default port for Flask
ENV PORT=8080

# Start the app
# Start the Flask app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers=1", "--threads=8", "--timeout=0", "main:app"]
