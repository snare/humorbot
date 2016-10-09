import logging
import json
import requests
import base64
import six
import textwrap
from scruffy import ConfigFile, PackageFile
from flask import Flask, request, jsonify, render_template, redirect
from slackclient import SlackClient

MORBO_USAGE = """
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
FRINK_USAGE = """
Display this help:
`/frink help`
Generate a still image for _don't mind if i do_:
`/frink don't mind if i do`
`/frink image don't mind if i do`
Generate a still image for search term _don't mind if i do_ with a different text overlay:
`/frink don't mind if i do -- snare sux`
`/frink image don't mind if i do -- snare sux`
Generate a selection of still images for _don't mind if i do_:
`/frink images don't mind if i do`
Generate a GIF for _don't mind if i do_:
`/frink gif don't mind if i do`
"""
MAX_IMAGES = 10
WRAP_WIDTH = 24
MORBO_BASE_URL = 'https://morbotron.com'
FRINK_BASE_URL = 'https://frinkiac.com'

log = logging.getLogger()

config = ConfigFile('~/.humourbot.conf', defaults=PackageFile('defaults.yaml'), apply_env=True, env_prefix='HBOT')
config.load()

app = Flask(__name__)


@app.route('/')
def index():
    """
    Render the home page which allows the user to add the app to their Slack team
    """
    return render_template('index.html', morbo_client_id=str(config.morbo_client_id),
                           frink_client_id=str(config.frink_client_id), installed=request.args.get('installed'))


@app.route('/slack', methods=['POST'])
def slack():
    """
    Handle initial / command from Slack
    """
    try:
        # Make sure we got a valid app token
        token = request.values.get('token')
        if token in [config.morbo_token, config.frink_token]:
            # Check if we were called from the Frinkiac app or the Morbotron app
            command = request.values.get('command')
            if 'morbo' in command:
                command = 'morbo'
                base = MORBO_BASE_URL
            elif 'frink' in command:
                command = 'frink'
                base = FRINK_BASE_URL
            else:
                raise Exception('Unknown command {}'.format(command))

            # Parse the command args
            args = request.values.get('text')
            d = request.values.to_dict()
            print("Got request: {}".format(d))
            url = None
            tokens = args.split()
            if len(tokens) and tokens[0] == 'help' or len(tokens) == 0:
                # Display usage
                if command.endswith('morbo'):
                    res = {'text': MORBO_USAGE.strip()}
                elif command.endswith('frink'):
                    res = {'text': FRINK_USAGE.strip()}
            elif len(tokens) and tokens[0] == 'gif':
                # Reassemble search string
                text = ' '.join(tokens[1:])

                # Separate search criteria and text overlay if there's --
                if '--' in text:
                    a = text.split('--')
                    crit = a[0].strip()
                    text = a[1].strip()
                else:
                    crit = text

                # Perform search
                search_result = search(crit, base=base)
                if len(search_result):
                    # Retrieve context frames for the gif using the first search result
                    # Maybe later we'll want to allow the user to select a frame to start with?
                    context = context_frames(search_result[0]['Episode'], search_result[0]['Timestamp'], base=base)
                    if len(context):
                        # Generate initial gif using the entire context and return an ephemeral message
                        url = gif_url(context[0]['Episode'], context[0]['Timestamp'], context[-1]['Timestamp'], text,
                                      base=base)
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
                                                'args': args,
                                                'command': command
                                            })
                                        },
                                        {
                                            'name': 'edit',
                                            'text': 'Edit',
                                            'type': 'button',
                                            'value': json.dumps({
                                                'args': args,
                                                'text': text,
                                                'episode': context[0]['Episode'],
                                                'context': [i['Timestamp'] for i in context],
                                                'start': context[0]['Timestamp'],
                                                'end': context[-1]['Timestamp'],
                                                'show_text': True,
                                                'command': command
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
                # Reassemble search string
                if len(tokens) and tokens[0] in ['image', 'images']:
                    text = ' '.join(tokens[1:])
                else:
                    text = ' '.join(tokens)

                # Separate search criteria and text overlay if there's --
                if '--' in text:
                    a = text.split('--')
                    crit = a[0].strip()
                    text = a[1].strip()
                else:
                    crit = text

                # Perform search
                search_result = search(crit, base=base)
                if len(search_result):
                    # If we're presenting multiple options as a preview...
                    if tokens[0] == 'images':
                        attachments = []
                        # Generate attachments for MAX_IMAGES options
                        for r in search_result[:min(MAX_IMAGES, len(search_result))]:
                            url = image_url(r['Episode'], r['Timestamp'], text, base=base)
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
                                            'args': args,
                                            'command': command
                                        })
                                    }
                                ]
                            })

                        # Add a cancel button
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

                        # Build an ephemeral message for the preview
                        res = {
                            'text': '',
                            'response_type': 'ephemeral',
                            'attachments': attachments
                        }
                    else:
                        # Otherwise, we're just going to immediately return an in_channel message for the first result
                        url = image_url(search_result[0]['Episode'], search_result[0]['Timestamp'], text, base=base)
                        res = {
                            'text': '',
                            'response_type': 'in_channel',
                            'attachments': [
                                {
                                    'title': '@{}: /{} {}'.format(d['user_name'], command, args),
                                    'fallback': text,
                                    'image_url': url
                                }
                            ]
                        }
                else:
                    # Search didn't match anything :()
                    res = {'text': "No match for '{}'".format(text), 'response_type': 'ephemeral'}
        else:
            res = {'text': "Token doesn't match", 'response_type': 'ephemeral'}
    except Exception as e:
        print("Exception processing request: {}".format(e))
        res = {'text': 'Error processing request.', 'response_type': 'ephemeral'}

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
            if data['command'] == 'frink':
                base = FRINK_BASE_URL
            else:
                base = MORBO_BASE_URL
            url = gif_url(data['episode'], data['start'], data['end'], data['text'] if data['show_text'] else '',
                          base=base)
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
                    'thumb_url': thumb_url(data['episode'], timestamp, base=base),
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
                            'args': data['args'],
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
                        'title': '@{}: /{} {}'.format(d['user']['name'], data['command'], data['args']),
                        'fallback': data['url'],
                        'image_url': data['url'],
                    }
                ]
            }
    except Exception as e:
        print(e)
        res = {'text': "Error processing action", 'response_type': 'ephemeral'}

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


class RequestFailedException(Exception):
    pass


def search(key, base=MORBO_BASE_URL):
    """
    Search Morbotron or Frinkiac
    """
    res = requests.get('{}/api/search?q={}'.format(base, key))
    if res.ok:
        return res.json()
    else:
        raise RequestFailedException()


def context_frames(episode, timestamp, before=4000, after=4000, base=MORBO_BASE_URL):
    """
    Get frames around the given timestamp.
    """
    url = '{base}/api/frames/{episode}/{ts}/{before}/{after}'.format(base=base, episode=episode, ts=timestamp,
                                                                     before=before, after=after)
    res = requests.get(url)
    if res.ok:
        return res.json()
    else:
        raise RequestFailedException()


def image_url(episode, timestamp, text='', base=MORBO_BASE_URL):
    """
    Return a frame URL based on an episode and timestamp.
    """
    b64 = base64.b64encode(six.b('\n'.join(textwrap.wrap(text, WRAP_WIDTH)))).decode('latin1')
    param = '?b64lines={}'.format(b64) if len(text) else ''
    return '{base}/meme/{episode}/{timestamp}.jpg{param}'.format(base=base, episode=episode,
                                                                 timestamp=timestamp, param=param)


def gif_url(episode, start, end, text='', base=MORBO_BASE_URL):
    """
    Return a GIF URL based on an episode and start and end timestamps.
    """
    b64 = base64.b64encode(six.b('\n'.join(textwrap.wrap(text, WRAP_WIDTH)))).decode('latin1')
    param = '?b64lines={}'.format(b64) if len(text) else ''
    return '{base}/gif/{episode}/{start}/{end}.gif{param}'.format(base=base, episode=episode,
                                                                  start=start, end=end, param=param)


def thumb_url(episode, timestamp, base=MORBO_BASE_URL):
    """
    Return a thumbnail URL based on an episode and timestamp.
    """
    return '{base}/img/{episode}/{timestamp}/small.jpg'.format(base=base, episode=episode, timestamp=timestamp)


def main():
    app.run()


if __name__ == '__main__':
    main()
