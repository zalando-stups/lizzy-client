.. image:: https://travis-ci.org/zalando/lizzy-client.svg?branch=master
   :target: https://travis-ci.org/zalando/lizzy-client
   :alt: Travis CI build status

.. image:: https://coveralls.io/repos/zalando/lizzy-client/badge.svg?branch=master&service=github
   :target: https://coveralls.io/github/zalando/lizzy-client?branch=master
   :alt: Coveralls status

Lizzy Client
============

Script to deploy Senza_ definitions using a Lizzy_ server.

Create a new stack
------------------

Use the `create` subcommand to create stacks. The syntax is `lizzy create [OPTIONS] DEFINITION IMAGE_VERSION`:

.. code-block::

    $ lizzy create -c config.yaml senza.yaml 1.0

For see more options use `lizzy create --help`.

List stacks
-----------
Use the `list` subcommand to list stacks:

.. code-block::

    $ lizzy list -c config.yaml

For see more options use `lizzy list --help`.

Change stack traffic
--------------------
Use the `traffic` subcommand to change the stacks traffic:

.. code-block::

    $ lizzy traffic -c config.yaml my_app 1.0 95

For see more options use `lizzy traffic --help`.

Deleting stacks
---------------
Use the `delete` subcommand to delete stacks:

.. code-block::

    $ lizzy delete -c config.yaml my_app 1.0

For see more options use `lizzy delete --help`.

Configuration
-------------
`token-url`, `lizzy-url` can be set on a configuration file:

.. code-block::

      lizzy-url: https://lizzyserver.example/
      token-url: https://token.url.example/access_token

Note that this two values must be set either on the configuration file or as a command line argument.

Authentication
--------------
Lizzy client works with Berry_ out of the box. To run it locally for testing purposes see `python-token's documentation
<https://github.com/zalando-stups/python-tokens#local-testing>`_.

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

.. _Berry: https://github.com/zalando-stups/berry
.. _Lizzy: https://github.com/zalando/lizzy
.. _Senza: https://github.com/zalando-stups/senza