import logging
import json
import requests
import six
import random
import os

from scruffy import ConfigFile, PackageFile
from flask import Flask, request, jsonify, render_template, redirect, send_from_directory
from slackclient import SlackClient
from .bot import Humorbot

log = logging.getLogger()
app = Flask(__name__)
config = None
hb = Humorbot()


@app.route('/')
def index():
    """
    Render the home page which allows the user to add the app to their Slack team
    """
    return render_template('index.html', morbo_client_id=str(config.morbo_client_id),
                           frink_client_id=str(config.frink_client_id), installed=request.args.get('installed'))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/privacy')
def privacy():
    """
    Display the privacy policy page.
    """
    return render_template('privacy.html')


@app.route('/usage')
def usage():
    """
    Display the usage page.
    """
    return render_template('usage.html')


def verify_token(func):
    """
    Decorator to verify that the app token in the request belongs to one of the
    ones passed through from the config.
    """
    def inner(*args, **kwargs):
        no_match = jsonify({'text': "Token doesn't match", 'response_type': 'ephemeral'})
        token = request.values.get('token')
        if token:
            if token in [config.morbo_token, config.frink_token]:
                res = func(*args, **kwargs)
            else:
                res = no_match
        else:
            try:
                d = json.loads(request.form.get('payload'))
                if d['token'] in [config.morbo_token, config.frink_token]:
                    res = func(*args, **kwargs)
                else:
                    res = no_match
            except:
                res = no_match
        return res

    return inner


@app.route('/slack', methods=['POST'], endpoint='slack')
@verify_token
def slack():
    """
    Handle initial / command from Slack
    """
    try:
        command = request.values.get('command').replace('/', '').strip()
        data = request.values.to_dict()

        log.debug("Got request: {}".format(data))

        res = hb.process_command(command, data)
    except Exception as e:
        log.exception("Exception processing request: {}".format(e))
        res = {'text': 'Error processing request.', 'response_type': 'ephemeral'}

    log.debug("Returning response: {}".format(res))

    return jsonify(res)


@app.route('/slacktion', methods=['POST'], endpoint='slacktion')
@verify_token
def slacktion():
    """
    Handle slack message actions.
    """
    try:
        data = json.loads(request.form.get('payload'))
        log.debug('Got action with payload: {}'.format(data))

        res = hb.process_action(data)
    except Exception as e:
        log.exception("Exception processing action: {}".format(e))
        res = {'text': "Error processing action", 'response_type': 'ephemeral'}
        raise

    return jsonify(res)


@app.route('/oauth/frink')
@app.route('/oauth/morbo')
@app.route('/oauth')
def oauth():
    """
    OAuth endpoint
    """
    if request.path.endswith('frink'):
        client_id = config.frink_client_id
        client_secret = config.frink_client_secret
    else:
        client_id = config.morbo_client_id
        client_secret = config.morbo_client_secret
    if request.values.get('error'):
        if request.values.get('error') == 'access_denied':
            print("User canceled authorisation")
        else:
            print("An error occurred: {}".format(request.values.get('error')))
        return redirect('/')
    else:
        d = {'code': request.args.get('code'), 'client_id': client_id, 'client_secret': client_secret}
        url = 'https://slack.com/api/oauth.access?client_id={client_id}&client_secret={client_secret}&code={code}'.format(**d)
        res = requests.get(url)
        if res.ok:
            d = res.json()
            print("Successful authentication for user id {} in team ID {} ({})".format(d['user_id'], d['team_id'],
                                                                                       d['team_name']))
            return redirect('/?installed=true')
        else:
            print("Failed to request OAuth token: {}".format(res))
            return redirect('/?installed=error')
