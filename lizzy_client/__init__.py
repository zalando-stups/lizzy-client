'''
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the 'License'); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
'''

import logging
import sys

import click
import requests

from .lizzy import Lizzy
from .token import get_token
from .configuration import load_configuration

# Parameters that must be set either in command line arguments or configuration
REQUIRED = ['user', 'password', 'lizzy_url', 'token_url']

requests.packages.urllib3.disable_warnings()  # Disable the security warnings


def init_logger(level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger('lizzy-client')
    formatter = logging.Formatter('%(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


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

    logger = init_logger()

    if configuration:
        options = load_configuration(configuration)
        if options is None:
            logger.error('Failed to load configuration file.')
            sys.exit(-1)
        user = options.get('user') or user
        password = options.get('password') or password
        lizzy_url = options.get('lizzy-url') or lizzy_url
        token_url = options.get('token-url') or token_url

    for parameter in REQUIRED:
        # verify is all required parameters are set either on command line arguments or configuration
        if not locals()[parameter]:
            parameter = parameter.replace('_', '-')  # convert python variable name to command line argument name
            logger.error('Error: Missing option "--%s".', parameter)
            exit(-1)

    access_token = get_token(token_url, user, password)
    if access_token is None:
        logger.error('Authentication failed.')
        sys.exit(-1)

    lizzy = Lizzy(lizzy_url, access_token)

    stack_id = lizzy.new_stack(image_version, keep_stacks, traffic, senza_yaml)
    if stack_id is None:
        logger.error('Deployment failed.')
        sys.exit(-1)
    logger.info('Stack ID: %s', stack_id)

    final_state = lizzy.wait_for_deployment(stack_id)

    if final_state == 'CF:CREATE_COMPLETE':
        logger.info('Deployment Successful')
        sys.exit(0)
    elif final_state == 'CF:ROLLBACK_COMPLETE':
        logger.error('Stack was rollback after deployment. Check you application log for possible reasons.')
        sys.exit(1)
    elif final_state == 'LIZZY:REMOVED':
        logger.error('Stack was removed before deployment finished.')
        sys.exit(1)
    else:
        logger.error('Deployment failed: %s', final_state)
        sys.exit(1)
