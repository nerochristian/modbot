# Build the React Frontend
FROM node:20 AS frontend-builder
WORKDIR /app/website
COPY website/package*.json ./
RUN npm install
COPY website/ ./
RUN npm run build

# Setup the Python Environment
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python source code
COPY . .

# Copy built frontend from the builder stage
COPY --from=frontend-builder /app/website/dist /app/website/dist

# Expose the port Render/DigitalOcean expects
EXPOSE 10547

# Start the bot
CMD ["python", "bot.py"]
