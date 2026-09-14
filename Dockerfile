FROM python:3.11-slim
RUN apt-get update && apt-get install -y unzip && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY keyauth_discord_bot.zip .
RUN unzip -o keyauth_discord_bot.zip || true
RUN pip install --no-cache-dir discord.py aiohttp python-dotenv
ENV PORT=8080
EXPOSE 8080
CMD ["python", "multi_bot.py"]
