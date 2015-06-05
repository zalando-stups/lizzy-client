'''
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the 'License'); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
'''

import sys

from clickclick import Action, error, info, fatal_error
import click
import requests
import yaml

from .lizzy import Lizzy
from .token import get_token
from .configuration import load_configuration

# Parameters that must be set either in command line arguments or configuration
REQUIRED = ['user', 'password', 'lizzy_url', 'token_url']

requests.packages.urllib3.disable_warnings()  # Disable the security warnings


@click.command()
@click.option('--configuration', '-c')
@click.option('--senza-yaml', required=True)
@click.option('--image-version', required=True)
@click.option('--keep-stacks', default=0)
@click.option('--traffic', default=100)
@click.option('--user', '-u')
@click.option('--password', '-p')
@click.option('--lizzy-url', '-l')
@click.option('--token-url', '-t')
def run(configuration: str,
        senza_yaml: str,
        image_version: str,
        keep_stacks: str,
        traffic: str,
        user: str,
        password: str,
        lizzy_url: str,
        token_url: str):

    if configuration:
        try:
            options = load_configuration(configuration)
        except FileNotFoundError:
            fatal_error('Configuration file not found.')
        except yaml.YAMLError:
            fatal_error('Error parsing YAML file.')

        user = options.get('user') or user
        password = password or options.get('password')
        lizzy_url = lizzy_url or options.get('lizzy-url')
        token_url = token_url or options.get('token-url')

    for parameter in REQUIRED:
        # verify is all required parameters are set either on command line arguments or configuration
        if not locals()[parameter]:
            parameter = parameter.replace('_', '-')  # convert python variable name to command line argument name
            fatal_error('Error: Missing option "--{parameter}".', parameter=parameter)

    with Action('Fetching authentication token..') as action:
        try:
            token_info = get_token(token_url, user, password)
            action.progress()
        except requests.RequestException as e:
            action.fatal_error('Authentication failed: {}'.format(e))

        try:
            access_token = token_info['access_token']
            action.progress()
        except KeyError:
            action.fatal_error('Authentication failed: "access_token" not on json.')

    lizzy = Lizzy(lizzy_url, access_token)

    with Action('Requesting new stack..') as action:
        try:
            stack_id = lizzy.new_stack(image_version, keep_stacks, traffic, senza_yaml)
        except requests.RequestException as e:
            action.fatal_error('Deployment failed:: {}'.format(e))

    info('Stack ID: {}'.format(stack_id))

    with Action('Wating for new stack..\n') as action:
        for status in lizzy.wait_for_deployment(stack_id):
            final_state = status
            info('.. '+status)

        if final_state == 'CF:CREATE_COMPLETE':
            info('Deployment Successful')
        elif final_state == 'CF:ROLLBACK_COMPLETE':
            error('Stack was rollback after deployment. Check you application log for possible reasons.')
        elif final_state == 'LIZZY:REMOVED':
            error('Stack was removed before deployment finished.')
        else:
            error('Deployment failed: {}'.format(final_state))
