Feature: License compatibility check
    Scenario: download the matrix file
        Given internet access is present
        When matrix file is not present
        Then download the matrix file
    Scenario: update the matrix file
        Given the matrix file is present
        And internet access is present
        Then compare timestamp against online oracle
        When the online timestamp is newer
        Then update the matrix file with the online one

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