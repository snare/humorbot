# -*- coding: utf-8 -*-
import re
import json
from random import choice
from .backend import *


MORBO_USAGE = """Display this help:
`/morbo help`
Generate a still image for _do the hustle_:
`/morbo do the hustle`
`/morbo image do the hustle`
Generate a still image for search term _do the hustle_ with a different text overlay (rather than the subtitles):
`/morbo do the hustle | do the bartman`
`/morbo image do the hustle | do the bartman`
Generate a still image for the search term _do the hustle_ with no text overlay:
`/morbo do the hustle |`
Generate a selection of still images for _do the hustle_:
`/morbo images do the hustle`
Generate a GIF for _do the hustle_:
`/morbo gif do the hustle`
Generate a GIF with search term _sure baby, i know it_ but text overlay _shut up baby, i know it_ (because Morbotron has the wrong subtitles so it won't match properly):
`/morbo gif sure baby, i know it | shut up baby, i know it`
Generate a selection of GIFs for _seymour_:
`/morbo gifs seymour`
"""

FRINK_USAGE = """Display this help:
`/frink help`
Generate a still image for _don't mind if i do_:
`/frink don't mind if i do`
`/frink image don't mind if i do`
Generate a still image for search term _don't mind if i do_ with a different text overlay (rather than the subtitles):
`/frink don't mind if i do | snare sux`
`/frink image don't mind if i do | snare sux`
Generate a still image for the search term _don't mind if i do_ with no text overlay:
`/morbo don't mind if i do |`
Generate a selection of still images for _don't mind if i do_:
`/frink images don't mind if i do`
Generate a GIF for _don't mind if i do_:
`/frink gif don't mind if i do`
Generate a GIF for _don't mind if i do_ with a different text overlay:
`/frink gif don't mind if i do | do mind if I don't`
Generate a selection of GIFs for _rebigulator_:
`/frink gifs rebigulator`
"""

MAX_IMAGES = 10
MAX_GIFS = 5


class Humorbot(object):
    def __init__(self):
        self.frink = Frinkiac()
        self.morbo = Morbotron()
        return super(Humorbot, self).__init__()

    def backend(self, name):
        """
        Return the backend based on the name.
        """
        if 'frink' in name:
            return self.frink
        else:
            return self.morbo

    def parse_args(self, text):
        """
        Parse arguments into the action, search query, and text overlay
        """
        # work out what action we got
        tokens = text.split()
        valid_actions = ['help', 'usage', 'image', 'images', 'random', 'gif', 'gifs']
        if len(tokens) and tokens[0] in valid_actions:
            action = tokens[0]
            tokens.pop(0)
        elif len(tokens) == 0:
            action = 'help'
        else:
            action = 'image'
        if action == 'usage':
            action = 'help'
        rest = ' '.join(tokens)

        # see if we got separate search string and text overlay
        tokens = re.split('(--|–|\|)', rest)
        if len(tokens) > 2:
            query = tokens[0]
            overlay = tokens[2]
        else:
            query = rest
            overlay = ''

        return (action.strip(), query.strip(), overlay.strip())

    def process_command(self, command, data):
        """
        Process a command sent to the app.
        """
        # Parse the command args
        (action, query, overlay) = self.parse_args(data['text'])

        log.debug(u"Processing /{} {} action with query '{}' and text overlay '{}'".format(command, action, query,
                                                                                           overlay))

        if action == 'help':
            # Display usage
            if 'morbo' in command:
                res = {'text': MORBO_USAGE}
            elif 'frink' in command:
                res = {'text': FRINK_USAGE}
        elif action in ['image', 'random']:
            res = self.image(data['user_name'], query, overlay, command, random=(action == 'random'))
        elif action == 'images':
            res = self.images(data['user_name'], query, overlay, command)
        elif action == 'gif':
            res = self.gif(data['user_name'], query, overlay, command)
        elif action == 'gifs':
            res = self.gifs(data['user_name'], query, overlay, command)

        return res

    def process_action(self, payload):
        """
        Process an action sent to the app by clicking an interactive button in
        a message.
        """
        action = payload['actions'][0]['name']
        if action == 'cancel':
            res = {'delete_original': True}
        elif action in ['edit', 'start', 'end', 'show_hide_text']:
            res = self.update_gif(payload)
        elif action == 'send':
            res = self.send(payload)

        return res

    def image(self, username, query, overlay='', command='morbo', random=False, multiple=False):
        """
        Implement the 'image' and 'random' actions.
        """
        backend = self.backend(command)
        search_result = backend.search(query)
        if len(search_result):
            r = choice(search_result) if random else search_result[0]
            args = u'{} | {}'.format(query, overlay) if overlay else '{}{}'.format('random ' if random else '', query)
            if not overlay:
                overlay = backend.caption_for_query(r['Episode'], r['Timestamp'], query)
            url = backend.image_url(r['Episode'], r['Timestamp'], overlay)
            res = {
                'text': '',
                'response_type': 'in_channel',
                'attachments': [
                    {
                        'title': u'@{}: /{} {}'.format(username, command, args),
                        'fallback': u'@{}: /{} {} | {}'.format(username, command, args, url),
                        'image_url': url
                    }
                ]
            }
        else:
            res = {'text': u"No match for '{}'".format(query), 'response_type': 'ephemeral'}

        return res

    def images(self, username, query, overlay='', command='morbo'):
        """
        Implement the 'images' action.
        """
        backend = self.backend(command)
        search_result = self.backend(command).search(query)

        # Generate attachments for MAX_IMAGES options
        attachments = []
        ol = overlay
        for r in search_result[:min(MAX_IMAGES, len(search_result))]:
            args = u'images {} | {}'.format(query, overlay) if overlay else u'images {}'.format(query)
            if not overlay:
                ol = backend.caption_for_query(r['Episode'], r['Timestamp'], query)
            url = backend.image_url(r['Episode'], r['Timestamp'], ol)
            attachments.append({
                'fallback': overlay,
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
                            'text': overlay,
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

        return res

    def gif(self, username, query, overlay='', command='morbo'):
        """
        Implement the 'gif' action
        """
        # Perform search
        backend = self.backend(command)
        search_result = backend.search(query)

        if len(search_result):
            # Retrieve context frames for the gif using the first search result
            # Maybe later we'll want to allow the user to select a frame to start with?
            context = backend.context_frames(search_result[0]['Episode'], search_result[0]['Timestamp'])
            if len(context):
                # Generate initial gif using the entire context and return an ephemeral message
                args = u'gif {} | {}'.format(query, overlay) if overlay else u'gif {}'.format(query)
                if not overlay:
                    overlay = backend.caption_for_query(search_result[0]['Episode'], search_result[0]['Timestamp'], query)
                url = backend.gif_url(context[0]['Episode'], context[0]['Timestamp'], context[-1]['Timestamp'], overlay)
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
                                        'text': overlay,
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
                                        'text': overlay,
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
            res = {'text': u"No match for '{}'".format(text), 'response_type': 'ephemeral'}

        return res

    def gifs(self, username, query, overlay='', command='morbo'):
        """
        Implement the 'gifs' action.
        """
        backend = self.backend(command)
        search_result = self.backend(command).search(query)

        # Generate attachments for MAX_GIFS options
        attachments = []
        ol = overlay
        for r in search_result[:min(MAX_GIFS, len(search_result))]:
            context = backend.context_frames(r['Episode'], r['Timestamp'])
            if len(context):
                args = u'gifs {} | {}'.format(query, overlay) if overlay else u'gifs {}'.format(query)
                if not overlay:
                    ol = backend.caption_for_query(r['Episode'], r['Timestamp'], query)
                url = backend.gif_url(context[0]['Episode'], context[0]['Timestamp'], context[-1]['Timestamp'], ol)
                attachments.append({
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
                                'text': ol,
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
                                'text': ol,
                                'episode': context[0]['Episode'],
                                'context': [i['Timestamp'] for i in context],
                                'start': context[0]['Timestamp'],
                                'end': context[-1]['Timestamp'],
                                'show_text': True,
                                'command': command
                            })
                        },
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

        return res

    def send(self, payload):
        """
        Send an edited GIF or selected image.
        """
        data = json.loads(payload['actions'][0]['value'])
        res = {
            'text': '',
            'response_type': 'in_channel',
            'delete_original': True,
            'attachments': [
                {
                    'title': u'@{}: /{} {}'.format(payload['user']['name'], data['command'], data['args']),
                    'fallback': u'@{}: /{} {} | {}'.format(payload['user']['name'], data['command'], data['args'],
                                                           data['url']),
                    'image_url': data['url'],
                }
            ]
        }

        return res

    def update_gif(self, payload):
        """
        Update a GIF in some way - change the start or end frame, toggle text overlay.
        """
        data = json.loads(payload['actions'][0]['value'])
        backend = self.backend(data['command'])
        url = backend.gif_url(data['episode'], data['start'], data['end'], data['text'] if data['show_text'] else '')
        attachments = []

        # Build an attachment with send, show/hide text and cancel buttons
        show_hide_data = dict(data)
        show_hide_data['show_text'] = not show_hide_data['show_text']
        attachments.append({
            'fallback': url,
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
                'thumb_url': backend.thumb_url(data['episode'], timestamp),
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

        # Build response
        res = {
            'text': '',
            'response_type': 'ephemeral',
            'attachments': attachments
        }

        return res
