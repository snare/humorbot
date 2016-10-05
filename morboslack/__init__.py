import logging
import json
import requests
from scruffy import ConfigFile, PackageFile
from flask import Flask, request, jsonify, render_template, redirect
from slackclient import SlackClient
from .morbotron import *

USAGE = """
*Usage*
Display this help:
`/morbo help`
Generate a still image for _do the hustle_:
`/morbo do the hustle`
`/morbo image do the hustle`
Generate a still image for search term _do the hustle_ with a different text overlay:
`/morbo do the hustle -- do the bartman`
`/morbo image do the hustle -- do the bartman`
Generate a selection of still images for _do the hustle_:
`/morbo images do the hustle`
Generate a GIF for _do the hustle_:
`/morbo gif do the hustle`
Generate a GIF with search term _sure baby, i know it_ but text overlay _shut up baby, i know it_ (because Morbotron has the wrong subtitles so it won't match properly):
`/morbo gif sure baby, i know it -- shut up baby, i know it`
"""
MAX_IMAGES = 10

log = logging.getLogger()

config = ConfigFile('~/.morboslack.conf', defaults=PackageFile('defaults.yaml'), apply_env=True, env_prefix='MORBO')
config.load()

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html', client_id=str(config.slack_client_id), installed=request.args.get('installed'))


@app.route('/slack', methods=['POST'])
def morbo():
    try:
        token = request.values.get('token')
        if token == config.slack_token:
            command = request.values.get('text')
            url = None
            tokens = command.split()
            if len(tokens) and tokens[0] == 'help':
                res = {'text': USAGE.strip()}
            elif len(tokens) and tokens[0] == 'gif':
                text = ' '.join(tokens[1:])
                if '--' in text:
                    a = text.split('--')
                    crit = a[0].strip()
                    text = a[1].strip()
                else:
                    crit = text
                search_result = search(crit)
                if len(search_result):
                    context = context_frames(search_result[0]['Episode'], search_result[0]['Timestamp'])
                    if len(context):
                        url = gif_url(context[0]['Episode'], context[0]['Timestamp'], context[-1]['Timestamp'], text)
                        res = {
                            'text': '',
                            'response_type': 'ephemeral',
                            'attachments': [
                                {
                                    'fallback': url,
                                    'image_url': url,
                                    'callback_id': 'gif_builder',
                                    'actions': [
                                        {
                                            'name': 'send',
                                            'text': 'Send',
                                            'type': 'button',
                                            'style': 'good',
                                            'value': json.dumps({
                                                'url': url,
                                                'text': text,
                                                'command': command
                                            })
                                        },
                                        {
                                            'name': 'edit',
                                            'text': 'Edit',
                                            'type': 'button',
                                            'value': json.dumps({
                                                'command': command,
                                                'text': text,
                                                'episode': context[0]['Episode'],
                                                'context': [i['Timestamp'] for i in context],
                                                'start': context[0]['Timestamp'],
                                                'end': context[-1]['Timestamp'],
                                                'show_text': True
                                            })
                                        },
                                        {
                                            'name': 'cancel',
                                            'text': 'Cancel',
                                            'type': 'button',
                                            'value': 'cancel'
                                        },
                                    ]
                                },
                            ]
                        }
                    else:
                        res = {'text': 'Failed to get context', 'response_type': 'ephemeral'}
                else:
                    res = {'text': "No match for '{}'".format(text), 'response_type': 'ephemeral'}
            else:
                if len(tokens) and tokens[0] in ['image', 'images']:
                    text = ' '.join(tokens[1:])
                else:
                    text = ' '.join(tokens)
                if '--' in text:
                    a = text.split('--')
                    crit = a[0].strip()
                    text = a[1].strip()
                else:
                    crit = text
                search_result = search(crit)
                if len(search_result):
                    if tokens[0] == 'images':
                        attachments = []
                        for r in search_result[:min(MAX_IMAGES, len(search_result))]:
                            url = image_url(r['Episode'], r['Timestamp'], text)
                            attachments.append({
                                'fallback': text,
                                'image_url': url,
                                'callback_id': 'image_preview',
                                'actions': [
                                    {
                                        'name': 'send',
                                        'text': 'Send',
                                        'type': 'button',
                                        'style': 'good',
                                        'value': json.dumps({
                                            'url': url,
                                            'text': text,
                                            'command': command
                                        })
                                    }
                                ]
                            })
                        attachments.append({
                            'callback_id': 'image_preview',
                            'actions': [
                                {
                                    'name': 'cancel',
                                    'text': 'Cancel',
                                    'type': 'button',
                                    'value': 'cancel'
                                }
                            ]
                        })
                        res = {
                            'text': '',
                            'response_type': 'ephemeral',
                            'attachments': attachments
                        }
                    else:
                        url = image_url(search_result[0]['Episode'], search_result[0]['Timestamp'], text)
                        res = {
                            'text': '',
                            'response_type': 'in_channel',
                            'attachments': [
                                {
                                    'fallback': text,
                                    'image_url': url
                                }
                            ]
                        }
                else:
                    res = {'text': "No match for '{}'".format(text), 'response_type': 'ephemeral'}
        else:
            res = {'text': "Token doesn't match", 'response_type': 'ephemeral'}
    except Exception as e:
        print(e)
        res = {'text': 'Error: {}'.format(e), 'response_type': 'ephemeral'}

    print("Returning response: {}".format(res))

    return jsonify(res)


@app.route('/slacktion', methods=['POST'])
def slacktion():
    """
    Handle slack message actions.
    """
    try:
        d = json.loads(request.form.get('payload'))
        print('Got action with payload: {}'.format(d))
        action = d['actions'][0]['name']
        if action == 'cancel':
            res = {'delete_original': True}
        elif action in ['edit', 'start', 'end', 'show_hide_text']:
            data = json.loads(d['actions'][0]['value'])
            url = gif_url(data['episode'], data['start'], data['end'], data['text'] if data['show_text'] else '')
            attachments = []

            # Build an attachment for each frame with a start and end button
            for timestamp in data['context']:
                start_data = dict(data)
                start_data['start'] = timestamp
                end_data = dict(data)
                end_data['end'] = timestamp
                i = data['context'].index(timestamp)
                if i >= data['context'].index(data['start']) and i <= data['context'].index(data['end']):
                    color = 'good'
                else:
                    color = ''
                attachments.append({
                    'text': 'Frame {} of episode {}'.format(timestamp, data['episode']),
                    'fallback': data['text'],
                    'thumb_url': thumb_url(data['episode'], timestamp),
                    'callback_id': 'gif_builder',
                    'color': color,
                    'actions': [
                        {
                            'name': 'start',
                            'text': 'Start frame',
                            'type': 'button',
                            'value': json.dumps(start_data)
                        },
                        {
                            'name': 'end',
                            'text': 'End frame',
                            'type': 'button',
                            'value': json.dumps(end_data)
                        },
                    ]
                })

            # Build an attachment with send, show/hide text and cancel buttons
            show_hide_data = dict(data)
            show_hide_data['show_text'] = not show_hide_data['show_text']
            attachments.append({
                'fallback': data['text'],
                'image_url': url,
                'callback_id': 'gif_builder',
                'actions': [
                    {
                        'name': 'send',
                        'text': 'Send',
                        'type': 'button',
                        'value': json.dumps({
                            'url': url,
                            'text': data['text'],
                            'command': data['command']
                        })
                    },
                    {
                        'name': 'show_hide_text',
                        'text': '{} text'.format('Hide' if data['show_text'] else 'Show'),
                        'type': 'button',
                        'value': json.dumps(show_hide_data)
                    },
                    {
                        'name': 'cancel',
                        'text': 'Cancel',
                        'type': 'button',
                        'value': 'cancel'
                    },
                ]
            })

            # Build response
            res = {
                'text': '',
                'response_type': 'ephemeral',
                'attachments': attachments
            }
        elif action == 'send':
            data = json.loads(d['actions'][0]['value'])
            res = {
                'text': '',
                'response_type': 'in_channel',
                'delete_original': True,
                'attachments': [
                    {
                        'title': '@{}: /morbo {}'.format(d['user']['name'], data['command']),
                        'fallback': data['url'],
                        'image_url': data['url'],
                    }
                ]
            }
    except Exception as e:
        print(e)
        res = {'text': "Error processing action", 'response_type': 'ephemeral'}

    return jsonify(res)


@app.route('/oauth')
def oauth():
    """
    OAuth endpoint
    """
    d = {'code': request.args.get('code'), 'client_id': config.slack_client_id,
         'client_secret': config.slack_client_secret}
    print(d)
    url = 'https://slack.com/api/oauth.access?client_id={client_id}&client_secret={client_secret}&code={code}'.format(**d)
    res = requests.get(url)
    if res.ok:
        print(res.json())
    else:
        print("Failed to request OAuth token: {}".format(res))

    return redirect('/?installed=true')


def main():
    app.run()


if __name__ == '__main__':
    main()
