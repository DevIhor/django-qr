#!/usr/bin/env python

from distutils.core import setup

setup(
    name='django-qr',
    version='0.1.0',
    author='DevIhor',
    author_email='ihorlutsiuk@gmail.com',
    packages=['qr'],
    url='https://github.com/DevIhor/django-qr',
    license='BSD licence, see LICENCE.md',
    description=('Django QR codes that allow the users to instantly sign in to the website on their mobile devices, '
                 'approve purchases and other secure operations'),
    long_description=open('README.md').read()[:-1],
    zip_safe=False,
    install_requires=[
        "Django >= 3.0",
        "qrcode >= 7.3",
        "redis >= 4.3",
        "Pillow >= 9.2"
    ],
)
