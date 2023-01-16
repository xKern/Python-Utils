from distutils.core import setup
from setuptools import find_packages


setup(
    name='pyutils',
    packages=find_packages('.'),
    version='0.1.1',
    license='MIT',
    description=('Common utility functions for python scripts'),
    author='ARX8x',
    author_email='root@xken.net',
    url='https://github.com/xKern/Python-Utils',
    keywords=['xKern', 'Utils', 'Utilities'],
    install_requires=[
        'pytz',
        'python-dotenv'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
)
