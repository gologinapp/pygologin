from setuptools import setup, find_packages
import os

with open("requirements.txt", "r") as f:
    install_requires = [line.strip() for line in f.readlines()]

# Read version from _version.py
version_file = os.path.join(os.path.dirname(__file__), 'gologin', '_version.py')
with open(version_file) as f:
    exec(f.read())

setup(
    name='gologin',
    version=__version__,
    packages=find_packages(),
    install_requires=install_requires,
    author='GoLogin',
    author_email='yuri@gologin.com',
    description='Official GoLogin python package',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/gologinapp/pygologin',
    python_requires='>=3.5',
    package_data={
        "gologin": ["py.typed"],
    },
)
