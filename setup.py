from setuptools import setup, find_packages

setup(
    name="humorbot",
    version="0.1",
    author="snare",
    author_email="snare@ho.ax",
    description=("A slack bot for Morbotron and Frinkiac"),
    license="MIT",
    keywords="humorbot",
    url="https://github.com/snare/humorbot",
    packages=find_packages(),
    install_requires=['flask', 'requests', 'scruffington', 'slack_client'],
    package_data={'humorbot': ['templates/*', 'defaults.yaml']},
    entry_points={
        'console_scripts': ['humorbot=humorbot:main']
    },
    zip_safe=False
)
