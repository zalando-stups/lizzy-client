import json
import time
from typing import Dict, List, Optional

import requests
import yaml
from clickclick import warning
from urlpath import URL

from .version import VERSION


def make_header(access_token: str):
    headers = dict()
    headers['Authorization'] = 'Bearer {}'.format(access_token)
    headers['Content-type'] = 'application/json'
    return headers


class Lizzy:
    def __init__(self, base_url: str, access_token: str):
        base_url = URL(base_url.rstrip('/'))
        self.api_url = base_url if base_url.path == '/api' else base_url / 'api'
        self.access_token = access_token

    @classmethod
    def get_output(cls, response: requests.Response) -> str:
        """
        Extracts the senza cli output from the response
        """
        output = response.headers['X-Lizzy-Output']  # type: str
        output = output.replace('\\n', '\n')  # unescape new lines
        lines = ('[AGENT] {}'.format(line) for line in output.splitlines())
        return '\n'.join(lines)

    @property
    def stacks_url(self) -> URL:
        return self.api_url / 'stacks'

    def delete(self, stack_id: str, region: str=None, dry_run: bool=False):
        url = self.stacks_url / stack_id

        header = make_header(self.access_token)
        data = {"dry_run": dry_run}
        if region:
            data["region"] = region

        request = url.delete(headers=header, json=data, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return self.get_output(request)

    def get_stack(self, stack_id: str, region: Optional[str]=None) -> dict:
        header = make_header(self.access_token)
        url = self.stacks_url / stack_id
        query = {}
        if region:
            query['region'] = region
        request = url.with_query(query).get(headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return request.json()

    def get_stacks(self, stack_reference: Optional[List[str]]=None,
                   region: Optional[str]=None) -> list:
        fetch_stacks_url = self.stacks_url
        query = {}
        if region:
            query['region'] = region
        if stack_reference:
            query['references'] = ','.join(stack_reference)

        fetch_stacks_url = fetch_stacks_url.with_query(query)

        response = fetch_stacks_url.get(headers=make_header(self.access_token),
                                        verify=False)

        lizzy_version = response.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))

        response.raise_for_status()
        return response.json()

    def new_stack(self,
                  keep_stacks: int,
                  new_traffic: int,
                  senza_yaml: dict,
                  stack_version: str,
                  disable_rollback: bool,
                  parameters: List[str],
                  region: Optional[str],
                  dry_run: bool,
                  tags: List[str]) -> (Dict[str, str], str):  # TODO put arguments in a more logical order
        """
        Requests a new stack.
        """
        header = make_header(self.access_token)
        data = {'senza_yaml': yaml.dump(senza_yaml),
                'stack_version': stack_version,
                'disable_rollback': disable_rollback,
                'dry_run': dry_run,
                'keep_stacks': keep_stacks,
                'new_traffic': new_traffic,
                'parameters': parameters,
                'tags': tags}
        if region:
            data['region'] = region

        request = self.stacks_url.post(json=data, headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return request.json(), self.get_output(request)

    def traffic(self, stack_id: str, percentage: int,
                region: Optional[str]=None):
        url = self.stacks_url / stack_id
        data = {"new_traffic": percentage}
        if region:
            data['region'] = region

        header = make_header(self.access_token)
        request = url.patch(json=data, headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        try:
            request.raise_for_status()
        except requests.RequestException:
            warning('Data Json:')
            print(json.dumps(data, indent=4))
            raise

    def get_traffic(self, stack_id: str, region: Optional[str]=None) -> dict:
        url = self.stacks_url / stack_id / 'traffic'
        query = {}
        if region:
            query['region'] = region
        url = url.with_query(query)

        header = make_header(self.access_token)
        response = url.get(headers=header, verify=False)
        lizzy_version = response.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        response.raise_for_status()
        return response.json()

    def wait_for_deployment(self, stack_id: str, region: Optional[str]=None) -> [str]:
        retries = 3
        while retries:
            try:
                stack = self.get_stack(stack_id, region=region)
                status = stack["status"]
                retries = 3  # reset the number of retries
                yield status
                if status.endswith('_FAILED') or status.endswith('_COMPLETE'):
                    return status
            except Exception as e:
                retries -= 1
                yield 'Failed to get stack ({retries} retries left): {exception}.'.format(retries=retries,
                                                                                          exception=repr(e))

            time.sleep(10)
