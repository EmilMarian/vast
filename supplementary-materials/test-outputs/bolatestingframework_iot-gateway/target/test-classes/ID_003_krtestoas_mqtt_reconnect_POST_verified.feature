Feature: IoT Gateway Health and Management API Tests

Background:
  * url 'http://192.168.1.109:48080'

Scenario: Test health check and reconnection APIs
  # Test health check endpoint
  Given path '/health'
  When method get
  Then status 200
  And match response.status == 'healthy'
  And match response.mqtt_broker == '#notnull'
  And match response.mqtt_connection == '#regex connected|disconnected'
  
  # Test MQTT reconnect functionality
  Given path '/mqtt/reconnect'
  When method post
  Then status 200
  And match response.status == 'success'
  And match response.message == 'MQTT reconnection initiated'