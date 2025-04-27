FROM python:3.9-slim

WORKDIR /app

# Copy the generator script
COPY generate_malicious_firmware.py /app/

# Install any necessary dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create firmware directory
RUN mkdir -p /app/firmware

# Generate various malicious firmware files with different ratios
RUN python generate_malicious_firmware.py --output /app/firmware/mild_firmware.sh --ratio 500 --size 5 && \
    python generate_malicious_firmware.py --output /app/firmware/medium_firmware.sh --ratio 2000 --size 10 && \
    python generate_malicious_firmware.py --output /app/firmware/severe_firmware.sh --ratio 5000 --size 20 && \
    python generate_malicious_firmware.py --output /app/firmware/extreme_firmware.sh --ratio 10000 --size 50

# Create a simple index.html to list available firmware files
RUN echo "<html><head><title>Malicious Firmware Repository</title></head><body>" > /app/firmware/index.html && \
    echo "<h1>Available Firmware Files</h1><ul>" >> /app/firmware/index.html && \
    echo "<li><a href='mild_firmware.sh'>Mild Attack (500:1 ratio, 5KB)</a></li>" >> /app/firmware/index.html && \
    echo "<li><a href='medium_firmware.sh'>Medium Attack (2000:1 ratio, 10KB)</a></li>" >> /app/firmware/index.html && \
    echo "<li><a href='severe_firmware.sh'>Severe Attack (5000:1 ratio, 20KB)</a></li>" >> /app/firmware/index.html && \
    echo "<li><a href='extreme_firmware.sh'>Extreme Attack (10000:1 ratio, 50KB)</a></li>" >> /app/firmware/index.html && \
    echo "</ul></body></html>" >> /app/firmware/index.html

# Expose HTTP server port
EXPOSE 38888

# Command to start a simple HTTP server
CMD ["python", "-m", "http.server", "38888", "--directory", "/app/firmware"]