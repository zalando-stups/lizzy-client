#!/usr/bin/env python3
"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys

from lizzy_client.version import VERSION

requirements = [
    'click>=6.3,<7.0',
    'clickclick>=0.15',
    'requests>=2.9.1',
    'pyyaml>=3.11',
    'python-dateutil>=2.5.0',
    'stups-tokens>=1.0.17',
    'environmental>=1.0',
    'urlpath>=1.1.2',
    'typing>=3.5.0.1'
]

test_requirements = [
    'pytest-cov>=2.2.1',
    'pytest>=2.9.0'
]


class PyTest(TestCommand):
    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.cov = None
        self.pytest_args = ['--cov-config', '.coveragerc', '--cov', 'lizzy_client', '--cov-report', 'term-missing']

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest

        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='lizzy-client',
    packages=find_packages(),
    version=VERSION,
    description='Lizzy-client',
    author='Zalando SE',
    url='https://github.com/zalando/lizzy-client',
    license='Apache License Version 2.0',
    install_requires=requirements,
    tests_require=test_requirements,
    cmdclass={'test': PyTest},
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    long_description='Lizzy-client',
    entry_points={'console_scripts': ['lizzy = lizzy_client.cli:main',
                                      'please = lizzy_client.cli:main',
                                      'pretty-please = lizzy_client.cli:main']},
)
