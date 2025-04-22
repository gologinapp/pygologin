from setuptools import setup, find_packages

with open("requirements.txt", "r") as f:
    install_requires = [line.strip() for line in f.readlines()]

setup(
    name='gologin',
    version='2025.04.22165958',
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
