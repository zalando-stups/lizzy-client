import pytest
from lizzy_client.utils import get_stack_refs, StackReference


@pytest.mark.parametrize(
    "input, expected_output",
    [
        (['foobar-stack'], [StackReference(name='foobar-stack', version=None)]),
        (['foobar-stack', '1'], [StackReference(name='foobar-stack', version='1')]),
        (['foobar-stack', '1', 'other-stack'],
         [StackReference(name='foobar-stack', version='1'), StackReference(name='other-stack', version=None)]),
        (['foobar-stack', 'v1', 'v2', 'v99', 'other-stack'],
         [StackReference(name='foobar-stack', version='v1'), StackReference(name='foobar-stack', version='v2'),
          StackReference(name='foobar-stack', version='v99'), StackReference(name='other-stack', version=None)]),
    ])
def test_get_stack_refs(input, expected_output):
    output = get_stack_refs(input)
    assert output == expected_output
