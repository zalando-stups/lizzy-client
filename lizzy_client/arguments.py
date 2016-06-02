"""
Common parameter types
"""

import os
import re
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

import click
import yaml

VERSION_PATTERN = re.compile(r'^[a-zA-Z0-9]+$')


class DefinitionParamType(click.ParamType):
    name = 'definition'

    def convert(self, value, param, ctx):
        if isinstance(value, str):
            try:
                url = value if '://' in value else 'file://{}'.format(quote(os.path.abspath(value)))
                # if '://' not in value:
                #     url = 'file://{}'.format(quote(os.path.abspath(value)))

                response = urlopen(url)
                data = yaml.safe_load(response.read())
            except URLError:
                self.fail('"{}" not found'.format(value), param, ctx)
        else:
            data = value
        for key in ['SenzaInfo']:
            if 'SenzaInfo' not in data:
                self.fail('"{}" entry is missing in YAML file "{}"'.format(key, value), param, ctx)
        return data


def validate_version(ctx, param, value):
    if not VERSION_PATTERN.match(value):
        raise click.BadParameter('Version must satisfy regular expression pattern "[a-zA-Z0-9]+"')
    return value
