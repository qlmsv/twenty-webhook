FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg2-binary
COPY app.py .
ENV PORT=10000
EXPOSE 10000
CMD ["python", "app.py"]
