"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

from typing import Optional
import yaml

# Parameters that must be set either in command line arguments or configuration
REQUIRED = ['user', 'password', 'lizzy-url', 'token-url']


class ConfigurationError(Exception):

    def __init__(self, message: str):
        self.message = message


class Parameters:

    def __init__(self,
                 configuration_path: Optional[str],
                 **kwargs):
        if configuration_path:
            try:
                with open(configuration_path) as configuration_file:
                    self.configuration_options = yaml.safe_load(configuration_file)
            except FileNotFoundError:
                raise ConfigurationError('Configuration file not found.')
            except yaml.YAMLError:
                raise ConfigurationError('Error parsing YAML file.')
        else:
            self.configuration_options = {}
        self.command_line_options = kwargs

    def __getattr__(self, item: str):
        config_name = item.replace('_', '-')
        return self.command_line_options.get(item) or self.configuration_options[config_name]

    def validate(self):
        """
        Verify if all needed parameters are set
        """
        for parameter in REQUIRED:
            # verify is all required parameters are set either on command line arguments or configuration
            cli_name = parameter.replace('_', '-')  # name on the command line
            if not (self.command_line_options.get(cli_name) or self.configuration_options.get(parameter)):
                raise ConfigurationError('Error: Missing option "--{parameter}".'.format(parameter=parameter))
