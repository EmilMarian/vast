# SECURE VERSION: Fixed sensor control endpoint with proper authorization

@app.route('/secure-control/<target_sensor_id>', methods=['POST'])
@require_auth  # Base authentication check
def secure_control_sensor(target_sensor_id):
    """
    SECURE ENDPOINT: Control a sensor with proper authorization checks
    
    This endpoint demonstrates proper authorization for sensor control:
    1. Authentication is required (via @require_auth decorator)
    2. Object-level authorization is enforced (checking ownership)
    3. Actions are validated and logged
    
    Expected JSON payload:
    {
        "action": "calibrate"|"set_fault"|"update_interval",
        "value": <value based on action>,
        "farm_id": <farm identifier>
    }
    """
    # Get authenticated user from request
    auth = request.authorization
    if not auth:
        return jsonify({"error": "Authentication required"}), 401
        
    # Get the requesting user's farm_id from their credentials
    user_farm_id = get_farm_id_for_user(auth.username)
    
    # Get request data
    data = request.get_json()
    if not data or "action" not in data or "value" not in data:
        return jsonify({"error": "action and value required"}), 400
    
    action = data["action"]
    value = data["value"]
    
    # Get the farm_id that owns the target sensor
    sensor_farm_id = get_farm_id_for_sensor(target_sensor_id)
    
    # OBJECT-LEVEL AUTHORIZATION CHECK:
    # Verify the authenticated user has permission to control this specific sensor
    if user_farm_id != sensor_farm_id:
        # Log the unauthorized attempt
        log.warning(f"Unauthorized attempt by {auth.username} (Farm {user_farm_id}) " +
                   f"to control sensor {target_sensor_id} belonging to Farm {sensor_farm_id}")
        
        # Return a generic error to avoid information disclosure
        return jsonify({"error": "Access denied"}), 403
    
    # Process the action only if authorized
    log.info(f"Authorized action {action} on sensor {target_sensor_id} by {auth.username}")
    
    # Process based on action type
    if action == "calibrate":
        try:
            calibrate_value = float(value)
            if not (15.0 <= calibrate_value <= 35.0):  # Input validation
                return jsonify({"error": "Calibration value out of allowed range (15-35°C)"}), 400
                
            # Only affect our sensor for demonstration
            if target_sensor_id == SENSOR_ID:
                sensor.base_temperature = calibrate_value
                log.info(f"Sensor {target_sensor_id} calibrated to {calibrate_value}°C")
                return jsonify({
                    "status": "success",
                    "message": f"Sensor {target_sensor_id} calibrated to {calibrate_value}°C"
                })
            else:
                # In a real system, this would communicate with the target sensor
                return jsonify({
                    "status": "success",
                    "message": f"Calibration command sent to sensor {target_sensor_id}"
                })
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid calibration value"}), 400
            
    elif action == "set_fault":
        if value not in ["none", "stuck", "drift", "spike", "dropout"]:
            return jsonify({"error": "Invalid fault mode"}), 400
            
        # Only affect our sensor for demonstration
        if target_sensor_id == SENSOR_ID:
            sensor.fault_mode = value
            log.info(f"Fault mode for sensor {target_sensor_id} set to {value}")
            return jsonify({
                "status": "success",
                "message": f"Fault mode for sensor {target_sensor_id} set to {value}"
            })
        else:
            # In a real system, this would communicate with the target sensor
            return jsonify({
                "status": "success",
                "message": f"Fault mode command sent to sensor {target_sensor_id}"
            })
            
    elif action == "update_interval":
        try:
            interval = int(value)
            if not (5 <= interval <= 300):  # Input validation
                return jsonify({"error": "Interval out of allowed range (5-300 seconds)"}), 400
                
            # Only affect our sensor for demonstration
            if target_sensor_id == SENSOR_ID:
                global MQTT_PUBLISH_INTERVAL
                MQTT_PUBLISH_INTERVAL = interval
                log.info(f"Publish interval for sensor {target_sensor_id} updated to {interval}s")
                return jsonify({
                    "status": "success",
                    "message": f"Publish interval for sensor {target_sensor_id} updated to {interval}s"
                })
            else:
                # In a real system, this would communicate with the target sensor
                return jsonify({
                    "status": "success",
                    "message": f"Interval update command sent to sensor {target_sensor_id}"
                })
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid interval value"}), 400
            
    else:
        return jsonify({"error": f"Unknown action: {action}"}), 400

# Helper functions for authorization (these would connect to a database in a real system)
def get_farm_id_for_user(username):
    """Get the farm ID associated with a username"""
    # In a real system, this would query a database
    user_to_farm = {
        "admin": "farm_admin",
        "farm_a_user": "farm_a",
        "farm_b_user": "farm_b",
        "farm_c_user": "farm_c"
    }
    return user_to_farm.get(username, "unknown")

def get_farm_id_for_sensor(sensor_id):
    """Get the farm ID that owns a particular sensor"""
    # In a real system, this would query a database
    sensor_to_farm = {
        "TEMP001": "farm_a",
        "TEMP002": "farm_a",
        "TEMP003": "farm_b",
        "TEMP004": "farm_c"
    }
    return sensor_to_farm.get(sensor_id, "unknown")