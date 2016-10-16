import nose
import json
from humorbot import *


def setup():
    global client
    client = app.test_client()


def teardown():
    pass


def test_image():
    match = {'text': '', 'attachments': [{
        'image_url': 'https://morbotron.com/meme/S05E02/278561.jpg?b64lines=ZG8gdGhlIGh1c3RsZQ==',
        'fallback': 'do the hustle'
    }], 'response_type': 'in_channel'}

    r = client.post('/slack', data=dict({'command': 'morbo', 'text': 'image do the hustle', 'team_id': 'TEAM_ID',
                                        'token': 'SLACK_TOKEN'}))
    assert json.loads(r.data.decode('latin1')) == match

    r = client.post('/slack', data=dict({'command': 'morbo', 'text': 'do the hustle', 'team_id': 'TEAM_ID',
                                        'token': 'SLACK_TOKEN'}))
    assert json.loads(r.data.decode('latin1')) == match


def test_gif():
    r = client.post('/slack', data=dict({'command': 'morbo', 'text': 'gif do the hustle', 'team_id': 'TEAM_ID',
                                        'token': 'SLACK_TOKEN'}))
    assert json.loads(r.data.decode('latin1')) == {'text': '', 'attachments': [{
        'image_url': 'https://morbotron.com/gif/S05E02/274591/282515.gif?b64lines=ZG8gdGhlIGh1c3RsZQ==',
        'fallback': 'do the hustle'
    }], 'response_type': 'in_channel'}
