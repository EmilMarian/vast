FROM python:3.9-slim

WORKDIR /app

COPY app.py requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ARG VERSION=latest
ENV VERSION=$VERSION

ENV MQTT_BROKER=localhost
ENV MQTT_PORT=1883
ENV MQTT_TOPIC=sensors/temperature
ENV MQTT_PUBLISH_INTERVAL=5
ENV SENSOR_ID=TEMP001
ENV FIRMWARE_PATH=/tmp/firmware
ENV UPDATE_SERVER=http://firmware-server.local
ENV SENSOR_FORMAT=binary

EXPOSE 12380

CMD ["python", "app.py"]
