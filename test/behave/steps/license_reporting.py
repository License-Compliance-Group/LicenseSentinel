"""A Behave step implementation/testing facility for
LicenseCompatibilityAnalyzer's potential reporting functionality"""

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
from behave.api.pending_step import StepNotImplementedError
from behave import given, when, then

@given('the calculation result is stored')
def step_impl(context):
    raise StepNotImplementedError('Given the calculation result is stored')


@when('the user requests a report')
def step_impl(context):
    raise StepNotImplementedError('When the user requests a report')


@then('generate a report')
def step_impl(context):
    raise StepNotImplementedError('Then generate a report')
