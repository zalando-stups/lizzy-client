import os.path
import time
from functools import wraps
from typing import List, Optional

import click
import dateutil.parser
import requests
import yaml
from clickclick import (Action, AliasedGroup, OutputFormat, error, fatal_error,
                        info, print_table, warning)
from tokens import InvalidCredentialsError
from yaml.error import YAMLError

from .arguments import (DefinitionParamType, dry_run_option, output_option,
                        region_option, remote_option, validate_version,
                        watch_option)
from .configuration import Configuration
from .lizzy import Lizzy
from .token import get_token
from .utils import get_stack_refs
from .version import VERSION

STYLES = {
    'RUNNING': {'fg': 'green'},
    'TERMINATED': {'fg': 'red'},
    'DELETE_COMPLETE': {'fg': 'red'},
    'ROLLBACK_COMPLETE': {'fg': 'red'},
    'CREATE_COMPLETE': {'fg': 'green'},
    'CREATE_FAILED': {'fg': 'red'},
    'CREATE_IN_PROGRESS': {'fg': 'yellow', 'bold': True},
    'DELETE_IN_PROGRESS': {'fg': 'red', 'bold': True},
    'ROLLBACK_IN_PROGRESS': {'fg': 'red', 'bold': True},
    'IN_SERVICE': {'fg': 'green'},
    'OUT_OF_SERVICE': {'fg': 'red'},
    'UPDATE_COMPLETE': {'fg': 'green'}
}

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
    'version': 'Ver.'
}

requests.packages.urllib3.disable_warnings()  # Disable the security warnings

main = AliasedGroup(context_settings=dict(help_option_names=['-h', '--help']))


def connection_error(e: requests.ConnectionError, fatal=True):
    reason = e.args[0].reason   # type: requests.packages.urllib3.exceptions.NewConnectionError
    _, pretty_reason = str(reason).split(':', 1)
    msg = ' {}'.format(pretty_reason)
    if fatal:
        fatal_error(msg)
    else:
        error(msg)


def agent_error(e: requests.HTTPError, fatal=True):
    """
    Prints an agent error and exits
    """
    data = e.response.json()
    details = data['detail']  # type: str

    if details:
        lines = ('[AGENT] {}'.format(line) for line in details.splitlines())
        msg = '\n' + '\n'.join(lines)
    else:
        msg = "[AGENT] {status} {title}".format_map(data)

    if fatal:
        fatal_error(msg)
    else:
        error(msg)


def display_user_friendly_agent_errors(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.ConnectionError as e:
            connection_error(e)
        except requests.HTTPError as e:
            agent_error(e)
    return _wrapper


def fetch_token(token_url: str, scopes: str, credentials_dir: str) -> str:  # TODO fix scopes to be really a list
    """
    Common function to fetch token
    :return:
    """

    with Action('Fetching authentication token..') as action:
        try:
            access_token = get_token(token_url, scopes, credentials_dir)
            action.progress()
        except InvalidCredentialsError as e:
            action.fatal_error(e)
    return access_token


def parse_stack_refs(stack_references: List[str]) -> List[str]:
    '''
    Check if items included in `stack_references` are Senza definition
    file paths or stack name reference. If Senza definition file path,
    substitute the definition file path by the stack name in the same
    position on the list.
    '''
    stack_names = []
    references = list(stack_references)
    references.reverse()
    while references:
        current = references.pop()
        # current that might be a file
        file_path = os.path.abspath(current)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path) as fd:
                    data = yaml.safe_load(fd)
                current = data['SenzaInfo']['StackName']
            except (KeyError, TypeError, YAMLError):
                raise click.UsageError('Invalid senza definition {}'.format(current))
        stack_names.append(current)
    return stack_names


def setup_lizzy_client(explicit_agent_url=None):
    config = Configuration()

    try:
        token_url = config.token_url
    except AttributeError:
        fatal_error('Environment variable OAUTH2_ACCESS_TOKEN_URL is not set.')

    scopes = config.scopes
    credentials_dir = config.credentials_dir

    access_token = fetch_token(token_url, scopes, credentials_dir)

    try:
        lizzy_url = explicit_agent_url or config.lizzy_url
    except AttributeError:
        fatal_error('Environment variable LIZZY_URL is not set.')

    return Lizzy(lizzy_url, access_token)


@main.command()
@click.argument('definition', type=DefinitionParamType())
@click.argument('version', callback=validate_version)
@click.argument('parameter', nargs=-1)
@region_option
@click.option('--disable-rollback', is_flag=True,
              help='Disable Cloud Formation rollback on failure')
@dry_run_option
@click.option('-f', '--force', is_flag=True, help='Ignore failing validation checks')
@click.option('-t', '--tag', help='Tags to associate with the stack.', multiple=True)
@click.option('--keep-stacks', type=int, help="Number of old stacks to keep")
@click.option('--traffic', default=0, type=click.IntRange(0, 100, clamp=True),
              help="Percentage of traffic for the new stack")
@remote_option
@click.option('--verbose', '-v', is_flag=True)
@display_user_friendly_agent_errors
def create(definition: dict, version: str,  parameter: list,
           region: str,
           disable_rollback: bool,
           dry_run: bool,
           force: bool,
           tag: List[str],
           keep_stacks: Optional[int],
           traffic: int,
           verbose: bool,
           remote: str,
           ):
    """Create a new Cloud Formation stack from the given Senza definition file"""
    lizzy = setup_lizzy_client(remote)
    parameter = parameter or []

    if not force:  # pragma: no cover
        # supporting artifact checking would imply copying a large amount of code
        # from senza, so it should be considered out of scope until senza
        # and lizzy client are merged
        warning("WARNING: Artifact checking is still not supported by lizzy-client.")

    with Action('Requesting new stack..') as action:
        new_stack, output = lizzy.new_stack(keep_stacks, traffic,
                                            definition, version,
                                            disable_rollback, parameter,
                                            region=region,
                                            dry_run=dry_run,
                                            tags=tag)

    stack_id = '{stack_name}-{version}'.format_map(new_stack)
    print(output)

    info('Stack ID: {}'.format(stack_id))

    if dry_run:
        info("Post deployment steps skipped")
        exit(0)

    with Action('Waiting for new stack...') as action:
        if verbose:
            print()  # ensure that new states will not be printed on the same line as the action

        last_state = None
        for state in lizzy.wait_for_deployment(stack_id, region=region):
            if state != last_state and verbose:
                click.echo(' {}'.format(state))
            else:
                action.progress()
            last_state = state

        # TODO be prepared to handle all final AWS CF states
        if last_state == 'ROLLBACK_COMPLETE':
            fatal_error('Stack was rollback after deployment. Check your application log for possible reasons.')
        elif last_state != 'CREATE_COMPLETE':
            fatal_error('Deployment failed: {}'.format(last_state))

    info('Deployment Successful')

    if traffic is not None:
        with Action('Requesting traffic change..'):
            try:
                lizzy.traffic(stack_id, traffic, region=region)
            except requests.ConnectionError as e:
                connection_error(e, fatal=False)
            except requests.HTTPError as e:
                agent_error(e, fatal=False)

    # TODO unit test this
    if keep_stacks is not None:
        versions_to_keep = keep_stacks + 1
        try:
            all_stacks = lizzy.get_stacks([new_stack['stack_name']], region=region)
        except requests.ConnectionError as e:
            connection_error(e, fatal=False)
            error("Failed to fetch old stacks. Old stacks WILL NOT BE DELETED")
        except requests.HTTPError as e:
            agent_error(e, fatal=False)
            error("Failed to fetch old stacks. Old stacks WILL NOT BE DELETED")
        else:
            sorted_stacks = sorted(all_stacks,
                                   key=lambda stack: stack['creation_time'])
            stacks_to_remove = sorted_stacks[:-versions_to_keep]
            with Action('Deleting old stacks..') as action:
                print()
                for old_stack in stacks_to_remove:
                    old_stack_id = '{stack_name}-{version}'.format_map(old_stack)
                    click.echo(' {}'.format(old_stack_id))
                    try:
                        lizzy.delete(old_stack_id, region=region)
                    except requests.ConnectionError as e:
                        connection_error(e, fatal=False)
                    except requests.HTTPError as e:
                        agent_error(e, fatal=False)


@main.command('list')
@click.argument('stack_ref', nargs=-1)
@click.option('--all', is_flag=True, help='Show all stacks, including deleted ones')
@remote_option
@region_option
@watch_option
@output_option
@display_user_friendly_agent_errors
def list_stacks(stack_ref: List[str], all: bool, remote: str, region: str,
                watch: int, output: str):
    """List Lizzy stacks"""
    lizzy = setup_lizzy_client(remote)
    stack_references = parse_stack_refs(stack_ref)

    while True:
        rows = []
        for stack in lizzy.get_stacks(stack_references, region=region):
            creation_time = dateutil.parser.parse(stack['creation_time'])
            rows.append({'stack_name': stack['stack_name'],
                         'version': stack['version'],
                         'status': stack['status'],
                         'creation_time': creation_time.timestamp(),
                         'description': stack['description']})

        rows.sort(key=lambda x: (x['stack_name'], x['version']))
        with OutputFormat(output):
            print_table('stack_name version status creation_time description'.split(),
                        rows, styles=STYLES, titles=TITLES)

        if watch:  # pragma: no cover
            time.sleep(watch)
            click.clear()
        else:
            break


@main.command('traffic')
@click.argument('stack_name')
@click.argument('stack_version', required=False)
@click.argument('percentage',
                type=click.IntRange(0, 100, clamp=True),
                required=False)
@region_option
@remote_option
@output_option
@display_user_friendly_agent_errors
def traffic(stack_name: str,
            stack_version: Optional[str],
            percentage: Optional[int],
            region: Optional[str],
            remote: Optional[str],
            output: Optional[str]):
    '''Manage stack traffic'''
    lizzy = setup_lizzy_client(remote)

    if percentage is None:
        stack_reference = [stack_name]

        with Action('Requesting traffic info..'):
            stack_weights = []
            for stack in lizzy.get_stacks(stack_reference, region=region):
                stack_id = '{stack_name}-{version}'.format_map(stack)
                traffic = lizzy.get_traffic(stack_id, region=region)
                stack_weights.append({
                    'stack_name': stack_name,
                    'version': stack['version'],
                    'identifier': stack_id,
                    'weight%': traffic['weight']
                })
        cols = 'stack_name version identifier weight%'.split()
        with OutputFormat(output):
            print_table(cols,
                        sorted(stack_weights, key=lambda x: x['identifier']))
    else:
        with Action('Requesting traffic change..'):
            stack_id = '{stack_name}-{stack_version}'.format_map(locals())
            lizzy.traffic(stack_id, percentage, region=region)


@main.command()
@click.argument('stack_ref', nargs=-1)
@region_option
@dry_run_option
@click.option('-f', '--force', is_flag=True, help='Allow deleting multiple stacks')
@remote_option
@display_user_friendly_agent_errors
def delete(stack_ref: List[str],
           region: str, dry_run: bool, force: bool, remote: str):
    """Delete Cloud Formation stacks"""
    lizzy = setup_lizzy_client(remote)
    stack_refs = get_stack_refs(stack_ref)
    all_with_version = all(stack.version is not None
                           for stack in stack_refs)

    # this is misleading but it's the current behaviour of senza
    # TODO Lizzy list (stack_refs) to see if it actually matches more than one stack
    # to match senza behaviour
    if (not all_with_version and not dry_run and not force):
        fatal_error('Error: {} matching stacks found. '.format(len(stack_refs)) +
                    'Please use the "--force" flag if you really want to delete multiple stacks.')

    # TODO pass force option to agent

    output = ''
    for stack in stack_refs:
        if stack.version is not None:
            stack_id = '{stack.name}-{stack.version}'.format(stack=stack)
        else:
            stack_id = stack.name

        with Action("Requesting stack '{stack_id}' deletion..", stack_id=stack_id):
            output = lizzy.delete(stack_id, region=region, dry_run=dry_run)

    print(output)


@main.command()
def version():
    """
    Prints Lizzy Client's version
    """
    print('Lizzy Client', VERSION)
