from clickclick import Action, OutputFormat, print_table, info, fatal_error, AliasedGroup, error
from tokens import InvalidCredentialsError
from typing import Optional, List
import click
import dateutil.parser
import requests
import time
from .lizzy import Lizzy
from .token import get_token
from .configuration import Configuration
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
    'UPDATE_COMPLETE': {'fg': 'green'}, }

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

main = AliasedGroup(context_settings=dict(help_option_names=['-h', '--help']))
output_option = click.option('-o', '--output', type=click.Choice(['text', 'json', 'tsv']), default='text',
                             help='Use alternative output format')
watch_option = click.option('-w', '--watch', type=click.IntRange(1, 300), metavar='SECS',
                            help='Auto update the screen every X seconds')


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
    output = data['detail']  # type: str
    lines = ('[AGENT] {}'.format(line) for line in output.splitlines())
    msg = '\n' + '\n'.join(lines)
    if fatal:
        fatal_error(msg)
    else:
        error(msg)


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


@main.command()
@click.option('--keep-stacks', type=int, help="Number of old stacks to keep")
@click.option('--traffic', default=100, type=click.IntRange(0, 100, clamp=True),
              help="Percentage of traffic for the new stack")
@click.option('--verbose', '-v', is_flag=True)
@click.option('--app-version', '-a',
              help='Application version, if provided will be used as the stack version and to register it in Kio.')
@click.option('--disable-rollback', is_flag=True, help='Disable Cloud Formation rollback on failure')
@click.argument('definition')  # TODO add definition type like senza
@click.argument('stack-version')
@click.argument('image_version')
@click.argument('senza_parameters', nargs=-1)
def create(definition: str, image_version: str, keep_stacks: int,
           traffic: int, verbose: bool, senza_parameters: list,
           app_version: Optional[str], stack_version: str,
           disable_rollback: bool):
    '''Deploy a new Cloud Formation stack'''
    senza_parameters = senza_parameters or []

    config = Configuration()

    access_token = fetch_token(config.token_url, config.scopes, config.credentials_dir)

    lizzy = Lizzy(config.lizzy_url, access_token)

    with Action('Requesting new stack..') as action:
        try:
            new_stack = lizzy.new_stack(image_version, keep_stacks, traffic,
                                        definition, stack_version, app_version,
                                        disable_rollback, senza_parameters)
            stack_id = '{stack_name}-{version}'.format_map(new_stack)
        except requests.ConnectionError as e:
            connection_error(e)
        except requests.HTTPError as e:
            agent_error(e)

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

        # TODO be prepared to handle all final AWS CF states
        if last_state == 'ROLLBACK_COMPLETE':
            fatal_error('Stack was rollback after deployment. Check your application log for possible reasons.')
        elif last_state != 'CREATE_COMPLETE':
            fatal_error('Deployment failed: {}'.format(last_state))

    info('Deployment Successful')

    if traffic is not None:
        with Action('Requesting traffic change..'):
            try:
                lizzy.traffic(stack_id, traffic)
            except requests.ConnectionError as e:
                connection_error(e, fatal=False)
            except requests.HTTPError as e:
                agent_error(e, fatal=False)

    # TODO unit test this
    if keep_stacks is not None:
        versions_to_keep = keep_stacks + 1
        try:
            all_stacks = lizzy.get_stacks([new_stack['stack_name']])
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
                        lizzy.delete(old_stack_id)
                    except requests.ConnectionError as e:
                        connection_error(e, fatal=False)
                    except requests.HTTPError as e:
                        agent_error(e, fatal=False)

    if app_version:
        info('You can approve this new version using the command:\n\n\t'
             '$ kio version approve {app_name} {version}'.format(
                 app_name=new_stack['stack_name'], version=app_version))


@main.command('list')
@click.argument('stack_ref', nargs=-1)
@click.option('--all', is_flag=True, help='Show all stacks, including deleted ones')
@watch_option
@output_option
def list_stacks(stack_ref: List[str], all: bool, watch: int, output: str):
    """List Lizzy stacks"""

    config = Configuration()

    access_token = fetch_token(config.token_url, config.scopes, config.credentials_dir)

    lizzy = Lizzy(config.lizzy_url, access_token)

    while True:
        # TODO reimplement all later
        try:
            stacks = lizzy.get_stacks(stack_ref)
        except requests.ConnectionError as e:
            connection_error(e)
        except requests.HTTPError as e:
            agent_error(e)

        rows = []
        for stack in stacks:
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


@main.command()
@click.argument('stack_name')
@click.argument('stack_version')
@click.argument('percentage', type=click.IntRange(0, 100, clamp=True))
def traffic(stack_name: str, stack_version: str, percentage: int):
    '''Switch traffic'''
    config = Configuration()

    access_token = fetch_token(config.token_url, config.scopes, config.credentials_dir)

    lizzy = Lizzy(config.lizzy_url, access_token)

    with Action('Requesting traffic change..'):
        stack_id = '{stack_name}-{stack_version}'.format_map(locals())
        try:
            lizzy.traffic(stack_id, percentage)
        except requests.ConnectionError as e:
            connection_error(e)
        except requests.HTTPError as e:
            agent_error(e)


@main.command()
@click.argument('stack_name')
@click.argument('stack_version')
def delete(stack_name: str, stack_version: str):
    '''Delete a single stack'''
    config = Configuration()

    access_token = fetch_token(config.token_url, config.scopes, config.credentials_dir)

    lizzy = Lizzy(config.lizzy_url, access_token)

    with Action('Requesting stack deletion..'):
        stack_id = '{stack_name}-{stack_version}'.format_map(locals())
        try:
            lizzy.delete(stack_id)
        except requests.ConnectionError as e:
            connection_error(e)
        except requests.HTTPError as e:
            agent_error(e)


@main.command()
def version():
    """
    Prints Lizzy Client's version
    """
    print('Lizzy Client', VERSION)
