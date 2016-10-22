import nose
import json
from humorbot.app import *
from humorbot.bot import *


HUSTLE_IMAGE_RES = {
    'text': '',
    'response_type': 'in_channel',
    'attachments': [{
        'fallback': '@someone: /morbo do the hustle | https://morbotron.com/meme/S05E02/278561.jpg?b64lines=4pmqIERvIHRoZSBIdXN0bGUuLi4g4pmq',
        'title': '@someone: /morbo do the hustle',
        'image_url': 'https://morbotron.com/meme/S05E02/278561.jpg?b64lines=4pmqIERvIHRoZSBIdXN0bGUuLi4g4pmq'
    }]
}

REBIGULATOR_IMAGE_RES = {
    'text': '',
    'response_type': 'in_channel',
    'attachments': [{
        'title': '@someone: /frink rebigulator',
        'fallback': '@someone: /frink rebigulator | https://frinkiac.com/meme/S08E01/740772.jpg?b64lines=VEhBVCBXT1VMRCBSRVFVSVJFIFNPTUUKU09SVCBPRiBBIFJFQklHVUxBVE9S',
        'image_url': 'https://frinkiac.com/meme/S08E01/740772.jpg?b64lines=VEhBVCBXT1VMRCBSRVFVSVJFIFNPTUUKU09SVCBPRiBBIFJFQklHVUxBVE9S'
    }]
}

HUSTLE_LOL_IMAGE_RES = {
    'text': '',
    'response_type': 'in_channel',
    'attachments': [{
        'fallback': '@someone: /morbo do the hustle | lol | https://morbotron.com/meme/S05E02/278561.jpg?b64lines=bG9s',
        'image_url': 'https://morbotron.com/meme/S05E02/278561.jpg?b64lines=bG9s',
        'title': '@someone: /morbo do the hustle | lol'
    }]
}


def setup():
    global client
    hb = Humorbot()


def test_parse_args():
    assert hb.parse_args('help') == ('help', '', '')
    assert hb.parse_args('usage') == ('help', '', '')
    assert hb.parse_args('do the hustle') == ('image', 'do the hustle', '')
    assert hb.parse_args('do the hustle -- do the bartman') == ('image', 'do the hustle', 'do the bartman')
    assert hb.parse_args('do the hustle | do the bartman') == ('image', 'do the hustle', 'do the bartman')
    assert hb.parse_args('do the hustle – do the bartman') == ('image', 'do the hustle', 'do the bartman')
    assert hb.parse_args('do the hustle – do the bartman   ') == ('image', 'do the hustle', 'do the bartman')
    assert hb.parse_args('do the hustle – do the bartman -- | –') == ('image', 'do the hustle', 'do the bartman')
    assert hb.parse_args('do the hustle --') == ('image', 'do the hustle', '')
    assert hb.parse_args('image do the hustle --') == ('image', 'do the hustle', '')
    assert hb.parse_args('images do the hustle') == ('images', 'do the hustle', '')
    assert hb.parse_args('images do the hustle -- do the bartman') == ('images', 'do the hustle', 'do the bartman')
    assert hb.parse_args('gif do the hustle') == ('gif', 'do the hustle', '')
    assert hb.parse_args('gif do the hustle -- do the bartman') == ('gif', 'do the hustle', 'do the bartman')


def test_image():
    assert hb.image('someone', 'do the hustle') == HUSTLE_IMAGE_RES
    assert hb.image('someone', 'rebigulator', command='frink') == REBIGULATOR_IMAGE_RES
    assert hb.image('someone', 'do the hustle', 'lol') == HUSTLE_LOL_IMAGE_RES
    d = hb.image('someone', 'do the hustle', 'lol', random=True)
    assert d['text'] == ''
    assert d['response_type'] == 'in_channel'
    assert len(d['attachments']) == 1


def test_images():
    res = hb.images('someone', 'do the hustle')
    assert len(res['attachments']) == 11


def test_gif():
    print(hb.gif('someone', 'do the hustle'))


def test_process_command_help():
    assert hb.process_command('morbo', {'text': 'help'}) == {'text': MORBO_USAGE}
    assert hb.process_command('morbo', {'text': 'usage'}) == {'text': MORBO_USAGE}
    assert hb.process_command('frink', {'text': 'help'}) == {'text': FRINK_USAGE}
    assert hb.process_command('frink', {'text': 'usage'}) == {'text': FRINK_USAGE}
    assert hb.process_command('morbo', {'text': ''}) == {'text': MORBO_USAGE}
    assert hb.process_command('frink', {'text': ''}) == {'text': FRINK_USAGE}


def test_process_command_image():
    assert hb.process_command('morbo', {'text': 'do the hustle', 'user_name': 'someone'}) == HUSTLE_IMAGE_RES
    assert hb.process_command('frink', {'text': 'rebigulator', 'user_name': 'someone'}) == REBIGULATOR_IMAGE_RES
    assert hb.process_command('morbo', {'text': 'do the hustle | lol', 'user_name': 'someone'}) == HUSTLE_LOL_IMAGE_RES
    assert hb.process_command('morbo', {'text': 'image do the hustle', 'user_name': 'someone'}) == HUSTLE_IMAGE_RES
    d = hb.image('someone', 'do the hustle', 'lol', random=True)
    assert d['text'] == ''
    assert d['response_type'] == 'in_channel'
    assert len(d['attachments']) == 1
