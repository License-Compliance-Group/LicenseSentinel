Feature: comparing two license trees
    Can compare two independent license trees and detect mismatches/invalid licensing

    Background: Two license trees (A and B) can be generated

    Scenario: Fill the gaps
        When one or both license trees are missing
        Then generate
    
    Scenario: Compare the trees
        Given that two trees are present 
        Then perform a comparison

    Scenario: Tree mismatch
        When a tree mismatch occurs 
        Then note it and return it later 

    Scenario: Invalid licensing
        When a branch has an invalid license 
        Then note it and return it later 

    Scenario: Trees are identical
        Given no invalid licensing 
        When trees are identical
        Then report a success state 

    