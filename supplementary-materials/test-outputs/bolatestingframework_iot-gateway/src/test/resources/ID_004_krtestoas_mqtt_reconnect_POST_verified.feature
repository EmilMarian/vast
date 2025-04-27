Feature: IoT Gateway BOLA Vulnerability Tests

Background:
  * url 'http://192.168.1.109:48080'

Scenario: Test authorization bypass through user ID enumeration
  # First access a legitimate user's sensors
  Given path '/users/user1/sensors'
  When method get
  Then status 200
  And match response != null
  And match response['TEMP001'] != null
  
  # Test access to different user's sensors without authentication (BOLA vulnerability)
  Given path '/users/premium_user/sensors'
  When method get
  Then status 200  # Should be 403 if properly secured
  And match response != null
  And match response['TEMP004'] != null
  And match response['TEMP004'].sensitive_data != null
  
  # Test access to admin user's sensors without authentication (BOLA vulnerability)
  Given path '/users/admin/sensors'
  When method get
  Then status 200  # Should be 403 if properly secured
  And match response != null
  
  # Test access to non-existent user
  Given path '/users/nonexistent/sensors'
  When method get
  Then status 404
  And match response.error == 'User nonexistent not found'