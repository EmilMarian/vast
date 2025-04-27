Feature: Test API for Broken Authentication/Authorization
Scenario: Verify that the /simulate/fault endpoint does not allow unauthorized access
  Given url 'http://192.168.1.109:12384/simulate/fault'
  And request username='admin' and password='password'
  When method post
  Then status 401
  And match response contains 'Unauthorized'