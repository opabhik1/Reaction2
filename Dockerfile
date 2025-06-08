FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
ENV PORT 8000  # Match your health check port
CMD ["python", "bot.py"]
