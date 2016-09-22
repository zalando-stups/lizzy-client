import os
import re
from collections import namedtuple
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

import click
import yaml

StackReference = namedtuple('StackReference', 'name version')


def read_parameter_file(parameter_file):  # copy pasted from Senza
    paras = []

    try:
        url = (parameter_file if '://' in parameter_file
               else 'file://{}'.format(quote(os.path.abspath(parameter_file))))

        response = urlopen(url)
    except URLError:
        raise click.UsageError('Can\'t read parameter file "{}"'.format(parameter_file))

    try:
        cfg = yaml.safe_load(response.read())
        for key, val in cfg.items():
            paras.append("{}={}".format(key, val))
    except yaml.YAMLError as e:
        raise click.UsageError('Error {}'.format(e))

    return paras


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
