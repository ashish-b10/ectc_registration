#!/usr/bin/env python3

from setuptools import setup

setup(
    name='ectc-registration-exporter',
    version='0.1',
    description='Exports ECTC tournament registration information from Google spreadsheets',
    url='http://www.ectc-online.org',
    author='Ashish Banerjee',
    author_email='fake_email_address@fake-domain.com',
    license='GPLv3',
    packages=['ectc_registration'],
    install_requires=[
        'google-api-python-client',
        'pyopenssl',
        'oauth2client',
    ]
)
