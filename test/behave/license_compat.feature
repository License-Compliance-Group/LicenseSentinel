Feature: License compatibility check
    Scenario: download the matrix file
        Given the matrix file is not present
        When internet access is present
        Then download the matrix file
    Scenario: update the matrix file
        Given the matrix file is present
        And we have internet access
        Then check file timestamp
        And check the online timestamp
        When the online timestamp is newer
        Then delete the local matrix file
        And download a new matrix file

    Scenario: check license compatibility
        Given the matrix file is present
        And we have a list of licenses
        Then retrieve necessary entries from the matrix
        And compare them against one another
        And store the result

    Scenario: create a compatibility report 
        Given the calculation result is stored
        When the user requests a report 
        Then generate a report