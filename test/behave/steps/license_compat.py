from behave import given, when, then
from behave.api.pending_step import StepNotImplementedError

@given('that we have internet access')
def step_impl(context):
    raise StepNotImplementedError('Given that we have internet access')


@then('we can download the matrix.')
def step_impl(context):
    raise StepNotImplementedError('Then we can download the matrix.')

@given(u'the matrix file is not present')
def step_impl(context):
    raise StepNotImplementedError(u'Given the matrix file is not present')


@when(u'internet access is present')
def step_impl(context):
    raise StepNotImplementedError(u'When internet access is present')


@then(u'download the matrix file')
def step_impl(context):
    raise StepNotImplementedError(u'Then download the matrix file')


@given(u'the matrix file is present')
def step_impl(context):
    raise StepNotImplementedError(u'Given the matrix file is present')


@given(u'we have internet access')
def step_impl(context):
    raise StepNotImplementedError(u'Given we have internet access')


@then(u'check file timestamp')
def step_impl(context):
    raise StepNotImplementedError(u'Then check file timestamp')


@then(u'check the online timestamp')
def step_impl(context):
    raise StepNotImplementedError(u'Then check the online timestamp')


@when(u'the online timestamp is newer')
def step_impl(context):
    raise StepNotImplementedError(u'When the online timestamp is newer')


@then(u'delete the local matrix file')
def step_impl(context):
    raise StepNotImplementedError(u'Then delete the local matrix file')


@then(u'download a new matrix file')
def step_impl(context):
    raise StepNotImplementedError(u'Then download a new matrix file')
