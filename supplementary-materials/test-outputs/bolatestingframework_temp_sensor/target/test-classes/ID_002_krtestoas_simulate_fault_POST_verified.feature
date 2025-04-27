Feature: Test Fault Simulation Authentication in Temperature Sensor

Background:
  * url 'http://192.168.1.109:12384'
  * def validAuth = function(){ return { username: 'admin', password: 'admin' } }

Scenario: Test Authentication for Fault Simulation Endpoint
  # Test access without authentication (should fail)
  Given path '/simulate/fault'
  And request {"fault_mode": "stuck"}
  When method post
  Then status 401
  And match response.error == 'Unauthorized'
  
  # Test access with valid credentials (should succeed)
  Given path '/simulate/fault'
  And request {"fault_mode": "stuck"}
  And header Authorization = call validAuth()
  When method post
  Then status 200
  And match response.status == 'success'
  And match response.fault_mode == 'stuck'
  
  # Reset fault mode after test
  Given path '/simulate/fault'
  And request {"fault_mode": "none"}
  And header Authorization = call validAuth()
  When method post
  Then status 200
  And match response.status == 'success'
  And match response.fault_mode == 'none'