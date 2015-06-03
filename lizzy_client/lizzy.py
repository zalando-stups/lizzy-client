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
import logging
import requests
import time

FINAL_STATES = ["CF:CREATE_COMPLETE",
                "CF:CREATE_FAILED",
                "CF:DELETE_COMPLETE",
                "CF:DELETE_FAILED",
                "CF:DELETE_IN_PROGRESS"
                "CF:ROLLBACK_COMPLETE",
                "CF:ROLLBACK_FAILED",
                "CF:ROLLBACK_IN_PROGRESS",
                "LIZZY:ERROR",
                "LIZZY:REMOVED"]

logger = logging.getLogger('lizzy-client.lizzy')


def make_header(access_token):
    headers = dict()
    headers['Authorization'] = 'Bearer {}'.format(access_token)
    headers['Content-type'] = 'application/json'
    return headers


class Lizzy:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url
        self.access_token = access_token

    def get_stack(self, stack_id) -> dict:
        header = make_header(self.access_token)
        url = "{base_url}/stacks/{stack_id}".format(base_url=self.base_url, stack_id=stack_id)
        try:
            request = requests.get(url, headers=header, verify=False)
        except requests.RequestException:
            logger.exception("Failed to get stack state.")
            return None

        if request.ok:
            try:
                return request.json()
            except ValueError:
                logger.error("Error decoding lizzy response: %s", request.text)
        else:
            logger.error("Failed to get stack state: Got HTTP %d status code on %s", request.status_code, url)
            return None

    def new_stack(self, image_version, keep_stacks, new_traffic, senza_yaml_path) -> str:
        logger.info('Requesting deployment')
        header = make_header(self.access_token)

        with open(senza_yaml_path) as senza_yaml_file:
            senza_yaml = senza_yaml_file.read()

        data = {'image_version': image_version,
                'keep_stacks': keep_stacks,
                'new_traffic': new_traffic,
                'senza_yaml': senza_yaml}
        url = "{base_url}/stacks/".format(base_url=self.base_url)
        try:
            request = requests.post(url, data=json.dumps(data), headers=header, verify=False)
        except requests.RequestException:
            logger.exception("Failed to deploy stack.")
            return None

        if request.ok:
            try:
                stack_info = request.json()
                return stack_info['stack_id']
            except ValueError:
                logger.error("Error decoding lizzy response: %s", request.text)
        else:
            logger.error("Failed to deploy stack: Got HTTP %d status code on %s.", request.status_code, url)
            return None

    def wait_for_deployment(self, stack_id):
        last_status = None
        retries = 3
        while retries:
            stack = self.get_stack(stack_id)

            if stack:
                retries = 3  # reset the number of retries
                status = stack["status"]
                if status != last_status:
                    logger.info("Status: %s", status)
                    last_status = status
                if status in FINAL_STATES:
                    return status
            else:
                retries -= 1
                logger.info("%d retries left.", retries)
            time.sleep(10)
        logger.error('Deployment failed')
