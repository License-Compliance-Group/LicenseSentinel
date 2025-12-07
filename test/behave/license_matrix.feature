Feature: Handling the license matrix
    Can properly manage the license file, offline or otherwise
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


