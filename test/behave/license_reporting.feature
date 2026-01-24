Feature: generates compatibility reports
    This will probably be relegated to an UI
    Scenario: create a compatibility report
        Given the calculation result is stored
        When the user requests a report
        Then generate a report