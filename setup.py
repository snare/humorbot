from setuptools import setup, find_packages

setup(
    name="morboslack",
    version="0.1",
    author="snare",
    author_email="snare@ho.ax",
    description=(""),
    license="MIT",
    keywords="morboslack",
    url="https://github.com/snare/morboslack",
    packages=find_packages(),
    install_requires=['flask', 'requests', 'scruffington', 'slack_client'],
    entry_points={
        'console_scripts': ['morboslack=morboslack:main']
    }
)
