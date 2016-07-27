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
                url = (value if '://' in value
                       else 'file://{}'.format(quote(os.path.abspath(value))))

                response = urlopen(url)
                data = yaml.safe_load(response.read())
            except URLError:
                self.fail('"{}" not found'.format(value), param, ctx)
        else:
            data = value
        if 'SenzaInfo' not in data:
            self.fail('"SenzaInfo" entry is missing in '
                      ' YAML file "{}"'.format(value),
                      param, ctx)
        return data


def validate_version(ctx, param, value):
    if not VERSION_PATTERN.match(value):
        raise click.BadParameter('Version must satisfy regular expression '
                                 'pattern "{}"'.format(VERSION_PATTERN.pattern))
    return value


dry_run_option = click.option('--dry-run',
                              is_flag=True,
                              help='No-op mode: show what would be deleted')

output_option = click.option('-o', '--output',
                             type=click.Choice(['text', 'json', 'tsv']),
                             default='text',
                             help='Use alternative output format')

region_option = click.option('--region',
                             envvar='AWS_DEFAULT_REGION',
                             metavar='AWS_REGION_ID',
                             help='AWS region ID (e.g. eu-west-1)')

remote_option = click.option('-r', '--remote',
                             help='URL for Agent')

watch_option = click.option('-w', '--watch',
                            type=click.IntRange(1, 300),
                            metavar='SECS',
                            help='Auto update the screen every X seconds')
