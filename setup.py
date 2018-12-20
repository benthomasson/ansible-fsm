#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['docopt',
                'pyyaml',
                'pyzmq',
                'gevent',
                'requests',
                'gevent_fsm',
                'ansible_task_worker']

dependency_links = [
                'git+https://github.com/benthomasson/ansible-task-worker.git#egg=ansible_task_worker-0.0.1']

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="Ben Thomasson",
    author_email='bthomass@redhat.com',
    dependency_links=dependency_links,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Ansible with FSMs",
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='ansible_fsm',
    name='ansible_fsm',
    packages=find_packages(include=['ansible_fsm']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/benthomasson/ansible_fsm',
    version='0.1.0',
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'ansible-fsm = ansible_fsm.cli:main',
            'send-event = ansible_fsm.send_event:main',
        ],
    }
)
