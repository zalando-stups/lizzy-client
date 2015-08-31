"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the 'License'); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

from clickclick import Action, FloatRange, OutputFormat, print_table, info, fatal_error
import click
import dateutil.parser
import requests
import time

from .lizzy import Lizzy
from .token import get_token, TokenException
from .configuration import ConfigurationError, Parameters

STYLES = {
    'CF:RUNNING': {'fg': 'green'},
    'CF:TERMINATED': {'fg': 'red'},
    'CF:DELETE_COMPLETE': {'fg': 'red'},
    'CF:ROLLBACK_COMPLETE': {'fg': 'red'},
    'CF:CREATE_COMPLETE': {'fg': 'green'},
    'CF:CREATE_FAILED': {'fg': 'red'},
    'CF:CREATE_IN_PROGRESS': {'fg': 'yellow', 'bold': True},
    'CF:DELETE_IN_PROGRESS': {'fg': 'red', 'bold': True},
    'CF:ROLLBACK_IN_PROGRESS': {'fg': 'red', 'bold': True},
    'CF:IN_SERVICE': {'fg': 'green'},
    'CF:OUT_OF_SERVICE': {'fg': 'red'},
    'LIZZY:NEW': {'fg': 'yellow', 'bold': True},
    'LIZZY:CHANGE': {'fg': 'yellow', 'bold': True},
    'LIZZY:DEPLOYING': {'fg': 'yellow', 'bold': True},
    'LIZZY:DEPLOYED': {'fg': 'green'},
    'LIZZY:REMOVED': {'fg': 'red'}}

TITLES = {
    'creation_time': 'Created',
    'logical_resource_id': 'Resource ID',
    'launch_time': 'Launched',
    'resource_status': 'Status',
    'resource_status_reason': 'Status Reason',
    'lb_status': 'LB Status',
    'private_ip': 'Private IP',
    'public_ip': 'Public IP',
    'resource_id': 'Resource ID',
    'instance_id': 'Instance ID',
    'version': 'Ver.'}

requests.packages.urllib3.disable_warnings()  # Disable the security warnings

main = click.Group()
output_option = click.option('-o', '--output', type=click.Choice(['text', 'json', 'tsv']), default='text',
                             help='Use alternative output format')
watch_option = click.option('-w', '--watch', type=click.IntRange(1, 300), metavar='SECS',
                            help='Auto update the screen every X seconds')


def common_options(function):
    default_configuration = '{}/lizzy.yaml'.format(click.get_app_dir('lizzy'))

    function = click.option('--password', '-p')(function)
    function = click.option('--user', '-u')(function)
    function = click.option('--client-secret', '-s')(function)
    function = click.option('--client-id', '-i')(function)
    function = click.option('--scopes', '-g')(function)
    function = click.option('--token-url', '-t')(function)
    function = click.option('--lizzy-url', '-l')(function)
    function = click.option('--configuration', '-c', default=default_configuration)(function)

    return function


def fetch_token(token_url: str, scopes: list,
                client_id: str, client_secret: str,
                user: str, password: str) -> str:
    """
    Common function to fetch token
    :return:
    """

    with Action('Fetching authentication token..') as action:
        try:
            access_token = get_token(token_url, scopes, client_id, client_secret, user, password)
            action.progress()
        except TokenException as e:
            action.fatal_error('Authentication failed: {}'.format(e))
    return access_token


@main.command()
@click.argument('definition')  # TODO add definition type like senza
@click.argument('image_version')
@common_options
@click.option('--keep-stacks', default=0)
@click.option('--traffic', default=100)
@click.option('--verbose', '-v', is_flag=True)
def create(definition: str,
           image_version: str,
           configuration: str,
           keep_stacks: str,
           traffic: str,
           verbose: bool,
           **kwargs):
    try:
        parameters = Parameters(configuration, **kwargs)
        parameters.validate()
    except ConfigurationError as e:
        fatal_error(e.message)

    access_token = fetch_token(parameters.token_url, parameters.scopes, parameters.client_id, parameters.client_secret,
                               parameters.user, parameters.password)

    lizzy = Lizzy(parameters.lizzy_url, access_token)

    with Action('Requesting new stack..') as action:
        try:
            stack_id = lizzy.new_stack(image_version, keep_stacks, traffic, definition)
        except requests.RequestException as e:
            action.fatal_error('Deployment failed: {}.'.format(e))

    info('Stack ID: {}'.format(stack_id))

    with Action('Waiting for new stack...') as action:
        if verbose:
            print()  # ensure that new states will not be printed on the same line as the action

        last_state = None
        for state in lizzy.wait_for_deployment(stack_id):
            if state != last_state and verbose:
                click.echo(' {}'.format(state))
            else:
                action.progress()
            last_state = state

        if last_state == 'CF:ROLLBACK_COMPLETE':
            fatal_error('Stack was rollback after deployment. Check you application log for possible reasons.')
        elif last_state == 'LIZZY:REMOVED':
            fatal_error('Stack was removed before deployment finished.')
        elif last_state != 'CF:CREATE_COMPLETE':
            fatal_error('Deployment failed: {}.'.format(last_state))

    info('Deployment Successful')


@main.command('list')
@click.argument('stack_ref', nargs=-1)
@common_options
@click.option('--all', is_flag=True, help='Show all stacks, including deleted ones')
@watch_option
@output_option
def list_stacks(configuration: str,
                stack_ref: str,
                all: bool,
                watch: int,
                output: str,
                **kwargs):
    """List Lizzy stacks"""

    try:
        parameters = Parameters(configuration, **kwargs)
        parameters.validate()
    except ConfigurationError as e:
        fatal_error(e.message)

    access_token = fetch_token(parameters.token_url, parameters.scopes, parameters.client_id, parameters.client_secret,
                               parameters.user, parameters.password)

    lizzy = Lizzy(parameters.lizzy_url, access_token)

    repeat = True

    while repeat:
        try:
            all_stacks = lizzy.get_stacks()
        except requests.RequestException as e:
            fatal_error('Failed to get stacks: {}'.format(e))

        if all:
            stacks = all_stacks
        else:
            stacks = [stack for stack in all_stacks if stack['status'] not in ['LIZZY:REMOVED']]

        if stack_ref:
            stacks = [stack for stack in stacks if stack['stack_name'] in stack_ref]

        rows = []
        for stack in stacks:
            creation_time = dateutil.parser.parse(stack['creation_time'])
            rows.append({'stack_name': stack['stack_name'],
                         'version': stack['stack_version'],
                         'image_version': stack['image_version'],
                         'status': stack['status'],
                         'creation_time': creation_time.timestamp()})

        rows.sort(key=lambda x: (x['stack_name'], x['version']))
        with OutputFormat(output):
            print_table('stack_name version image_version status creation_time'.split(),
                        rows, styles=STYLES, titles=TITLES)

        if watch:
            time.sleep(watch)
            click.clear()
        else:
            repeat = False


@main.command()
@click.argument('stack_name')
@click.argument('stack_version')
@click.argument('percentage', type=FloatRange(0, 100, clamp=True))
@common_options
def traffic(stack_name: str,
            stack_version: str,
            percentage: int,
            configuration: str,
            **kwargs):
    try:
        parameters = Parameters(configuration, **kwargs)
        parameters.validate()
    except ConfigurationError as e:
        fatal_error(e.message)

    access_token = fetch_token(parameters.token_url, parameters.scopes, parameters.client_id, parameters.client_secret,
                               parameters.user, parameters.password)

    lizzy = Lizzy(parameters.lizzy_url, access_token)

    with Action('Requesting traffic change..'):
        stack_id = '{stack_name}-{stack_version}'.format_map(locals())
        lizzy.traffic(stack_id, percentage)


@main.command()
@click.argument('stack_name')
@click.argument('stack_version')
@common_options
def delete(stack_name: str,
           stack_version: str,
           configuration: str,
           **kwargs):
    try:
        parameters = Parameters(configuration, **kwargs)
        parameters.validate()
    except ConfigurationError as e:
        fatal_error(e.message)

    access_token = fetch_token(parameters.token_url, parameters.scopes, parameters.client_id, parameters.client_secret,
                               parameters.user, parameters.password)

    lizzy = Lizzy(parameters.lizzy_url, access_token)

    with Action('Requesting stack deletion..'):
        stack_id = '{stack_name}-{stack_version}'.format_map(locals())
        lizzy.delete(stack_id)
