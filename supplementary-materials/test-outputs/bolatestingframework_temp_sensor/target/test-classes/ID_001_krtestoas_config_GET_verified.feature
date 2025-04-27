Feature: Testing Broken Authentication and Authorization in Temperature Sensor

Background:
  * url 'http://192.168.1.109:12384'

Scenario: Test Authentication for Protected Configuration Endpoint
  # Test access without authentication (should fail)
  Given path '/config'
  When method get
  Then status 401
  And match response.error == 'Unauthorized'
  
  # Test access with invalid credentials (should fail)
  Given path '/config'
  And configure basicAuthFunction = function() { return 'user:wrongpass' }
  When method get
  Then status 401
  And match response.error == 'Unauthorized'
  
  # Test access with valid credentials (should succeed)
  Given path '/config'
  And configure basicAuthFunction = function() { return 'admin:admin' }
  When method get
  Then status 200
  And match response.sensor_id == 'TEMP004'
  And match response.type == 'temperature'
  And match response.mqtt_topic == 'sensors/temperature'
  
  # Clear basic auth
  * configure basicAuthFunction = null