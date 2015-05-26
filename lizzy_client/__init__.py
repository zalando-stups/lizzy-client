"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import json

import click
import requests

URL = "https://token.auth.zalando.com/access_token?json=True"


def make_header(access_token):
    headers = dict()
    headers['Authorization'] = 'Bearer {}'.format(access_token)
    headers['Content-type'] = 'application/json'
    return headers


def get_token(url, user, password):
    token_info = requests.get(url=url, auth=(user, password)).json()
    return token_info


def request_new_deployment(access_token, image_version, keep_stacks, new_traffic, senza_yaml_path):
    header = make_header(access_token)

    with open(senza_yaml_path) as senza_yaml_file:
        senza_yaml = senza_yaml_file.read()

    data = {'image_version': image_version,
            'keep_stacks': keep_stacks,
            'new_traffic': new_traffic,
            'senza_yaml': senza_yaml}
    request = requests.post('http://127.0.0.1:8080/deploy/', data=json.dumps(data), headers=header)
    return request.json()

@click.command()
@click.option('--image-version', required=True)
@click.option('--keep-stacks', default=1)
@click.option('--new-traffic', default=100)
@click.option('--senza-yaml', required=True)
@click.option('--user')
@click.password_option('--password')
def run(image_version, keep_stacks, new_traffic, senza_yaml, user, password):
    token_info = get_token(URL, user, password)
    access_token = token_info['access_token']
    request_new_deployment(access_token, image_version, keep_stacks, new_traffic, senza_yaml)

