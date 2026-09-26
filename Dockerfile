FROM python:3.11

# Install system dependencies (FFmpeg & Opus library)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Explicitly install discord.py and dependencies directly
RUN pip install --upgrade pip && \
    pip install --no-cache-dir discord.py PyNaCl edge-tts gTTS aiohttp python-dotenv

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "multi_bot.py"]
