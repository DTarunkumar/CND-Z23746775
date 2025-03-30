# Step 1: Base image
FROM python:3.10-slim

# Step 2: Set working directory
WORKDIR /app

# Step 3: Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Step 4: Install pytest and run tests
COPY tests/ ./tests/
RUN pip install pytest && pytest tests/

# Step 5: Copy the rest of your code
COPY . .

# Step 6: Set environment variable for Flask
ENV PORT=8080

# Step 7: Run the application
CMD ["python", "main.py"]
