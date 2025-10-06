# --- Build Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN pip install --upgrade pip

# Copy only requirements to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies, creating a wheel for each
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from the build stage
COPY --from=builder /wheels /wheels

# Install the dependencies from the wheels, which is faster and more reliable
RUN pip install --no-cache-dir /wheels/*

# Copy the application code
COPY . .

# Set the PORT environment variable for Cloud Run.
ENV PORT 8080

# Set the command to start the Uvicorn server.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
