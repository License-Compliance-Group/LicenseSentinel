@requires_license_list
Feature: performs license compatibility checks
    Can verify multiple licenses in a project

    Background: We assume a project exists and it has been scanned in any way,
    giving us access to a list of licenses used therein.
        Given a list of licenses

    Scenario: check license compatibility
        When a comparison is requested
        Then retrieve necessary entries from the matrix and compare them against one another
        And store the result
