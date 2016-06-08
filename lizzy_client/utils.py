from collections import namedtuple
import re
import yaml


StackReference = namedtuple('StackReference', 'name version')


def get_stack_refs(refs: list):  # copy pasted from Senza
    """
    Returns a list of stack references with name and version.
    """
    refs = list(refs)
    refs.reverse()
    stack_refs = []
    last_stack = None
    while refs:
        ref = refs.pop()
        if last_stack is not None and re.compile(r'v[0-9][a-zA-Z0-9-]*$').match(ref):
            stack_refs.append(StackReference(last_stack, ref))
        else:
            try:
                with open(ref) as fd:
                    data = yaml.safe_load(fd)
                ref = data['SenzaInfo']['StackName']
            except (OSError, IOError):
                # It's still possible that the ref is a regex
                pass

            if refs:
                version = refs.pop()
            else:
                version = None
            stack_refs.append(StackReference(ref, version))
            last_stack = ref
    return stack_refs
