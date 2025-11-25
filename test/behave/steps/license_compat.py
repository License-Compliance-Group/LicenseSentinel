from behave import given, when, then
from behave.api.pending_step import StepNotImplementedError

from src.analyzer.license_compatibility_analyzer\
    import LicenseCompatibilityAnalyzer as LCA

@given('that we have internet access')
def step_impl(context):
    raise StepNotImplementedError('Given that we have internet access')


@then('we can download the matrix.')
def step_impl(context):
    raise StepNotImplementedError('Then we can download the matrix.')

@given('the matrix file is not present')
def step_impl(context):
    raise StepNotImplementedError('Given the matrix file is not present')


@when('internet access is present')
def step_impl(context):
    raise StepNotImplementedError('When internet access is present')


@then('download the matrix file')
def step_impl(context):
    raise StepNotImplementedError('Then download the matrix file')


@given('the matrix file is present')
def step_impl(context):
    raise StepNotImplementedError('Given the matrix file is present')


@given('we have internet access')
def step_impl(context):
    raise StepNotImplementedError('Given we have internet access')


@then('check file timestamp')
def step_impl(context):
    raise StepNotImplementedError('Then check file timestamp')


@then('check the online timestamp')
def step_impl(context):
    raise StepNotImplementedError('Then check the online timestamp')


@when('the online timestamp is newer')
def step_impl(context):
    raise StepNotImplementedError('When the online timestamp is newer')


@then('delete the local matrix file')
def step_impl(context):
    raise StepNotImplementedError('Then delete the local matrix file')


@then('download a new matrix file')
def step_impl(context):
    raise StepNotImplementedError('Then download a new matrix file')

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
