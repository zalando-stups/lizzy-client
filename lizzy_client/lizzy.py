"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

from typing import Optional, List
from clickclick import warning
from urlpath import URL
from .version import VERSION
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


def make_header(access_token: str):
    headers = dict()
    headers['Authorization'] = 'Bearer {}'.format(access_token)
    headers['Content-type'] = 'application/json'
    return headers


class Lizzy:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = URL(base_url)
        self.access_token = access_token

    @property
    def stacks_url(self) -> URL:
        return self.base_url / 'stacks'

    def delete(self, stack_id: str):
        url = self.stacks_url / stack_id

        header = make_header(self.access_token)
        request = url.delete(headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()

    def get_stack(self, stack_id: str) -> dict:
        header = make_header(self.access_token)
        url = self.stacks_url / stack_id
        request = url.get(headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return request.json()

    def get_stacks(self) -> list:
        header = make_header(self.access_token)
        request = self.stacks_url.get(headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return request.json()

    def new_stack(self,
                  image_version: str,
                  keep_stacks: int,
                  new_traffic: int,
                  senza_yaml_path: str,
                  stack_version: Optional[str],
                  application_version: Optional[str],
                  disable_rollback: bool,
                  parameters: List[str]) -> str:
        """
        Requests a new stack.
        """
        header = make_header(self.access_token)

        with open(senza_yaml_path) as senza_yaml_file:
            senza_yaml = senza_yaml_file.read()

        data = {'image_version': image_version,
                'disable_rollback': disable_rollback,
                'keep_stacks': keep_stacks,
                'new_traffic': new_traffic,
                'parameters': parameters,
                'senza_yaml': senza_yaml}

        if application_version:
            data['application_version'] = application_version

        if stack_version:
            data['stack_version'] = stack_version

        request = self.stacks_url.post(data=json.dumps(data, sort_keys=True), headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return request.json()

    def traffic(self, stack_id: str, percentage: int):
        url = self.stacks_url / stack_id
        data = {"new_traffic": percentage}

        header = make_header(self.access_token)
        request = url.patch(data=json.dumps(data), headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        try:
            request.raise_for_status()
        except requests.RequestException:
            warning('Data Json:')
            print(json.dumps(data, indent=4))
            raise

    def wait_for_deployment(self, stack_id: str) -> [str]:
        retries = 3
        while retries:
            try:
                stack = self.get_stack(stack_id)
                status = stack["status"]
                retries = 3  # reset the number of retries
                yield status
                if status in FINAL_STATES:
                    return status
            except Exception as e:
                retries -= 1
                yield 'Failed to get stack ({retries} retries left): {exception}.'.format(retries=retries,
                                                                                          exception=repr(e))

            time.sleep(10)
