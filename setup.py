#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='JSMon',
    packages=find_packages(),
    version='1.0',
    description="A python script that monitors JavaScript files.",
    long_description=open('README.md').read(),
    author='r0bre',
    author_email='mail@r0b.re',
    license='MIT',
    url='https://github.com/robre/jsmon',
    install_requires=['requests', 'jsbeautifier', 'python-decouple','slack_sdk'],
)
