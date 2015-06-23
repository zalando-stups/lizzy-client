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


def make_header(access_token):
    headers = dict()
    headers['Authorization'] = 'Bearer {}'.format(access_token)
    headers['Content-type'] = 'application/json'
    return headers


class Lizzy:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url
        self.access_token = access_token

    @property
    def stacks_url(self):
        return "{base_url}/stacks".format(base_url=self.base_url)

    def delete(self, stack_id: str):
        url = "{base_url}/stacks/{stack_id}".format(base_url=self.base_url, stack_id=stack_id)

        header = make_header(self.access_token)
        request = requests.delete(url, headers=header, verify=False)
        request.raise_for_status()

    def get_stack(self, stack_id) -> dict:
        header = make_header(self.access_token)
        url = "{base_url}/stacks/{stack_id}".format(base_url=self.base_url, stack_id=stack_id)
        request = requests.get(url, headers=header, verify=False)
        request.raise_for_status()
        return request.json()

    def get_stacks(self) -> list:
        header = make_header(self.access_token)
        url = "{base_url}/stacks".format(base_url=self.base_url)
        request = requests.get(url, headers=header, verify=False)
        request.raise_for_status()
        return request.json()

    def new_stack(self, image_version, keep_stacks, new_traffic, senza_yaml_path) -> str:
        header = make_header(self.access_token)

        with open(senza_yaml_path) as senza_yaml_file:
            senza_yaml = senza_yaml_file.read()

        data = {'image_version': image_version,
                'keep_stacks': keep_stacks,
                'new_traffic': new_traffic,
                'senza_yaml': senza_yaml}

        request = requests.post(self.stacks_url, data=json.dumps(data), headers=header, verify=False)
        request.raise_for_status()
        stack_info = request.json()
        return stack_info['stack_id']

    def traffic(self, stack_id: str, percentage: int):
        url = "{base_url}/stacks/{stack_id}".format(base_url=self.base_url, stack_id=stack_id)
        data = {"new_traffic": percentage}

        header = make_header(self.access_token)
        request = requests.patch(url, data=json.dumps(data), headers=header, verify=False)
        request.raise_for_status()

    def wait_for_deployment(self, stack_id: str) -> [str]:
        last_status = None
        retries = 3
        while retries:
            try:
                stack = self.get_stack(stack_id)

                retries = 3  # reset the number of retries
                status = stack["status"]
                if status != last_status:
                    last_status = status
                    yield status
                if status in FINAL_STATES:
                    return status
            except Exception as e:
                retries -= 1
                yield 'Failed to get stack ({retries} retries left): {exception}.'.format(retries=retries, exception=e)

            time.sleep(10)
        return None
