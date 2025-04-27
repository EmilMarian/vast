Feature: Test Temperature Sensor Calibration Functionality

Background:
  * url 'http://192.168.1.109:12384'
  # Using temperature-sensor-04 as example
  * def validAuth = {username: 'admin', password: 'admin'}
  * def invalidAuth = {username: 'user', password: 'wrongpass'}

Scenario: Attempt sensor calibration without authentication
  Given path '/config/calibrate'
  And request { "calibration_offset": 1.5 }
  When method post
  Then status 401
  And match response.error == 'Unauthorized'

Scenario: Attempt sensor calibration with invalid credentials
  Given path '/config/calibrate'
  And request { "calibration_offset": 1.5 }
  And header Authorization = call invalidAuth
  When method post
  Then status 401
  And match response.error == 'Unauthorized'

Scenario: Successful sensor calibration with valid credentials
  # First check current configuration
  Given path '/config'
  And header Authorization = call validAuth
  When method get
  Then status 200
  And match response.sensor_id == 'TEMP004'
  
  # Perform calibration
  Given path '/config/calibrate'
  And request { "calibration_offset": 1.5 }
  And header Authorization = call validAuth
  When method post
  Then status 200
  And match response.status == 'success'
  And match response.calibration_offset == 1.5
  And match response.calibrated_reading != null
  
  # Reset calibration after test
  Given path '/config/calibrate'
  And request { "calibration_offset": 0.0 }
  And header Authorization = call validAuth
  When method post
  Then status 200
  And match response.status == 'success'
  And match response.calibration_offset == 0.0