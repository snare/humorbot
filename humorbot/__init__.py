import logging
import sys
from scruffy import ConfigFile, PackageFile
from flask import Flask, request, jsonify, render_template, redirect, send_from_directory
from slackclient import SlackClient

config = ConfigFile('~/.humourbot.conf', defaults=PackageFile('defaults.yaml'), apply_env=True, env_prefix='HBOT')
config.load()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if config.debug_logging else logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)

from . import app
app.config = config

log = logging.getLogger()


def main():
    app.app.run()


if __name__ == '__main__':
    app.app.run(debug=True)
