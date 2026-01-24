"""A Behave step implementation/testing facility for
LicenseCompatibilityAnalyzer"""

# pylint: disable=not-callable, missing-function-docstring, function-redefined
# Why?
# not-callable: @given('xxx') is standard Behave configuration, pylint
#               chooses to complain
# missing-function-docstring: most tests are oneliners, docstrings remove
#                             readability
# function-redefined: Behave explicitly states that step_impl is the default
#                     step name and it need not be unique
# https://behave.readthedocs.io/en/latest/tutorial/#python-step-implementations

# I would consider moving those new checks into a CI/CD pipeline soon
from behave import given, when, then


@given('a list of licenses')
def step_impl(context):
    context.licenses_list = [
        "BSD-1-Clause","BSD-2-Clause","BSD-3-Clause"
    ]

@when('a comparison is requested')
def step_impl(context): # pylint: disable=unused-argument
    assert True # can we control this from here?

@then('retrieve necessary entries from the matrix and compare them against one another')
def step_impl(context):
    assert context.lca.calculate_license_compatibility(context.licenses_list) \
    != (None, None)


@then('store the result')
def step_impl(context):
    context.lca.calculate_license_compatibility(context.licenses_list)
    assert context.lca.last_comparison_result[0] == "Yes"
