Feature: IoT Gateway API Data Access Tests

Background:
  * url 'http://192.168.1.109:48080'

Scenario: Test sensor data retrieval with different authorization scenarios
  # Test access to a specific sensor's data
  # Note: Gateway doesn't use API keys, so this test verifies basic data access
  Given path '/data/TEMP001'
  When method get
  Then status 200
  And match response != null
  And match response.sensor_id == 'TEMP001'
  And match response.type == 'temperature'
  
  # Test access to non-existent sensor
  Given path '/data/NONEXISTENT'
  When method get
  Then status 404
  And match response.error == 'Sensor not found'