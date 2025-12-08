"""A Behave step implementation/testing facility for
LicenseComparator"""

# pylint: disable=not-callable, missing-function-docstring, function-redefined
# Why?
# not-callable: @given('xxx') is standard Behave configuration, pylint
#               chooses to complain
# missing-function-docstring: most tests are oneliners, docstrings remove
#                             readability
# function-redefined: Behave explicitly states that step_impl is the default
#                     step name and it need not be unique
# https://behave.readthedocs.io/en/latest/tutorial/#python-step-implementations

from behave.api.pending_step import StepNotImplementedError
from behave import given, when, then
@when('one or both license trees are missing')
def step_impl(context):
    raise StepNotImplementedError('When one or both license trees are missing')


@then('generate')
def step_impl(context):
    raise StepNotImplementedError('Then generate')


@given('that two trees are present')
def step_impl(context):
    raise StepNotImplementedError('Given that two trees are present')


@then('perform a comparison')
def step_impl(context):
    raise StepNotImplementedError('Then perform a comparison')


@when('a tree mismatch occurs')
def step_impl(context):
    raise StepNotImplementedError('When a tree mismatch occurs')


@then('note it and return it later')
def step_impl(context):
    raise StepNotImplementedError('Then note it and return it later')


@when('a branch has an invalid license')
def step_impl(context):
    raise StepNotImplementedError('When a branch has an invalid license')


@given('no invalid licensing')
def step_impl(context):
    raise StepNotImplementedError('Given no invalid licensing')


@when('trees are identical')
def step_impl(context):
    raise StepNotImplementedError('When trees are identical')


@then('report a success state')
def step_impl(context):
    raise StepNotImplementedError('Then report a success state')