FROM python:3.12-slim

WORKDIR /app

COPY v2/requirements.txt /app/v2/requirements.txt
RUN pip install --no-cache-dir -r /app/v2/requirements.txt

COPY v2 /app/v2
RUN mkdir -p /data

ENV JOB_RADAR_DB=/data/jobs.db
EXPOSE 8000

CMD ["uvicorn", "v2.radar:app", "--host", "0.0.0.0", "--port", "8000"]
