Lizzy Client
============

Script to deploy Senza_ definitions using a Lizzy_ server.

Usage
-----

.. code-block::

    Usage: __main__.py [OPTIONS]

    Options:
      --configuration
      --senza-yaml TEXT      [required]
      --image-version TEXT   [required]
      --keep-stacks INTEGER
      --new-traffic INTEGER
      --user TEXT
      --password TEXT
      --token-url TEXT
      --lizzy-url TEXT
      --help                 Show this message and exit.

Configuration
-------------
`user`, `password`, `token-url`, `lizzy-url` can be set on a configuration file:

.. code-block::

      user: USERNAME
      password: PASSWORD
      lizzy-url: https://lizzyserver.example/
      token-url: https://token.url.example/access_token

Note that this four values must be set either on the configuration file or as a command line argument.

License
-------
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

.. _Lizzy: https://github.com/zalando/lizzy
.. _Senza: https://github.com/zalando-stups/senza