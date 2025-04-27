Feature: Authorization Bypass: User ID Enumeration
Background:
   * url 'http://192.168.1.109:48080'

Scenario: Detect and prevent unauthorized access through User ID enumeration
    Given path '/users/{user_id}/sensors'
    And param user_id = 'user123'
    And header Authorization = 'Bearer <user_token>'
    When method get
    Then status 403
    And match response contains 'Unauthorized access attempt detected.'