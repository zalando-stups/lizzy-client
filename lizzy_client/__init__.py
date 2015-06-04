"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import logging
import sys

import click
import requests

from .lizzy import Lizzy
from .token import get_token

requests.packages.urllib3.disable_warnings()  # Disable the security warnings

logger = logging.getLogger('lizzy-client')
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.setLevel(logging.INFO)


@click.command()
@click.option('--image-version', required=True)
@click.option('--keep-stacks', default=0)
@click.option('--new-traffic', default=100)
@click.option('--senza-yaml', required=True)
@click.option('--user', required=True)
@click.password_option('--password', required=True)
@click.option('--token-url', required=True)
@click.option('--lizzy-url', required=True)
def run(image_version: str,
        keep_stacks: str,
        new_traffic: str,
        senza_yaml: str,
        user: str,
        password: str,
        token_url: str,
        lizzy_url: str):

    access_token = get_token(token_url, user, password)
    if access_token is None:
        logger.error('Authentication failed.')
        sys.exit(-1)

    lizzy = Lizzy(lizzy_url, access_token)

    stack_id = lizzy.new_stack(image_version, keep_stacks, new_traffic, senza_yaml)
    if stack_id is None:
        logger.error('Deployment failed.')
        sys.exit(-1)
    logger.info("Stack ID: %s", stack_id)

    final_state = lizzy.wait_for_deployment(stack_id)

    if final_state == "CF:CREATE_COMPLETE":
        logger.info('Deployment Successful')
        sys.exit(0)
    elif final_state == "CF:ROLLBACK_COMPLETE":
        logger.error("Stack was rollback after deployment. Check you application log for possible reasons.")
        sys.exit(1)
    elif final_state == "LIZZY:REMOVED":
        logger.error("Stack was removed before deployment finished.")
        sys.exit(1)
    else:
        logger.error('Deployment failed: %s', final_state)
        sys.exit(1)
