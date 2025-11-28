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

import datetime 

from behave import given, when, then
from behave.api.pending_step import StepNotImplementedError

from src.analyzer.license_compatibility_analyzer\
    import LicenseCompatibilityAnalyzer as LCA

@given('internet access is present')
def step_internet_present(context):
    context.lca = LCA()
    assert context.lca.verify_internet_access()


@when('matrix file is not present')
def step_matrix_file_not_present(context):
    # Ensure the file is not present
    context.lca.delete_matrix_file()
    assert not context.lca.matrix_file_present()

@then('download the matrix file')
def step_download_matrix_file(context):
    context.lca.update_json()
    # Make sure the file is present
    assert context.lca.matrix_file_present()

@given('the matrix file is present')
def step_impl(context):
    context.lca = LCA()
    if not context.lca.matrix_file_present():
        context.lca.update_json()
    # Make sure the file is present
    assert context.lca.matrix_file_present()


@then('compare timestamp against online oracle')
def step_impl(context):
    context.lca.check_timestamp()


@when('the online timestamp is newer')
def step_impl(context):
    # Guarantee that for testing purposes
    override_datetime = datetime.datetime.fromisoformat(
        '2005-04-02T21:37:00+0000'
        )
    online_datetime = context.lca.get_online_timestamp()
    assert online_datetime >= override_datetime


@then('update the matrix file with the online one')
def step_impl(context):
    # We want to enforce a download
    # Discard the offline file
    context.lca.delete_matrix_file()
    context.lca.update_json()
    # The local and offline timestamps should be identical
    # Unless the oracle changed during the test (then just rerun)
    assert context.lca.get_local_timestamp() == \
    context.lca.get_online_timestamp()
    

@given('we have a list of licenses')
def step_impl(context):
    raise StepNotImplementedError('Given we have a list of licenses')


@then('retrieve necessary entries from the matrix')
def step_impl(context):
    raise StepNotImplementedError('Then retrieve necessary entries from the matrix')


@then('compare them against one another')
def step_impl(context):
    raise StepNotImplementedError('Then compare them against one another')


@then('store the result')
def step_impl(context):
    raise StepNotImplementedError('Then store the result')


@given('the calculation result is stored')
def step_impl(context):
    raise StepNotImplementedError('Given the calculation result is stored')


@when('the user requests a report')
def step_impl(context):
    raise StepNotImplementedError('When the user requests a report')


@then('generate a report')
def step_impl(context):
    raise StepNotImplementedError('Then generate a report')