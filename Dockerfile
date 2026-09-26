FROM python:3.11

# Install system dependencies (FFmpeg, Opus library, build essentials, libffi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libopus-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install discord.py voice dependencies (pynacl and davey)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir discord.py pynacl davey edge-tts gTTS aiohttp python-dotenv

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "multi_bot.py"]
