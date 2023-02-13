.. Release Process

Release Process
===============

Binary Release Process
++++++++++++++++++++++

#. Scan code for vulnerablities, currently using Snyk
#. Scrub source code of any private or sensitive HMD data
#. Add Apache 2.0 license file as LICENSE.txt in project root directory
#. Add any technology specific license metadata to reference Apache 2.0, e.g. ``license`` field in ``setup.py``
#. Update README.md and docs/ to publish to Knowledge Base
#. Add HMD CLI commands for each technology to be released under ``release.commands`` in ``manifest.json``