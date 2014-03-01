#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup
setup(name='clifa',
	version='0.2.2',
	description='Pretty online train connection api client for your shell. Based on pyefa.',
	author='Nils Martin Klünder',
	author_email='nomoketo@nomoketo.de',
	url='https://github.com/NoMoKeTo/pyefa',
	license='Apache',
	py_modules=['clifa', 'clifa_launch'],
	entry_points={
		'console_scripts': [
			'clifa = clifa_launch:launch'
		]
	},
	classifiers=[
		'Intended Audience :: End Users/Desktop',
		'Programming Language :: Python',
		'Natural Language :: English',
		'License :: OSI Approved :: Apache Software License'],
	install_requires=['pyefa'],
	)
