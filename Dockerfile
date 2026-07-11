FROM python:3.10-slim

# Install system dependencies (FFmpeg is required for Whisper audio processing!)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Whisper model weights during build to cache them
# This prevents timeouts and runtime download overhead during container startup
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

# Copy project code
COPY . .

# Set default host and port environment variables
ENV CPE_HOST=0.0.0.0
ENV CPE_PORT=8000
ENV LLM_PROVIDER=mock
ENV WHISPER_MODEL_SIZE=tiny
ENV WHISPER_DEVICE=cpu

EXPOSE 8000

# Start FastAPI server
CMD ["python", "run_server.py"]
