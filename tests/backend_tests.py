import nose
from humorbot import *


def setup():
    pass


def teardown():
    pass


def test_search():
    res = search('do the hustle')
    assert len(res) == 36


def test_context_frames():
    res = context_frames('S09E06', 729604)
    assert len(res) == 38


def test_image_url():
    assert image_url('S09E06', 729604) == 'https://morbotron.com/meme/S09E06/729604.jpg'
    assert image_url('S09E06', 729604, 'xxx') == 'https://morbotron.com/meme/S09E06/729604.jpg?b64lines=eHh4'


def test_thumb_url():
    assert thumb_url('S09E06', 729604) == 'https://morbotron.com/img/S09E06/729604/small.jpg'


def test_gif_url():
    assert gif_url('S09E06', 729604, 729605) == 'https://morbotron.com/gif/S09E06/729604/729605.gif'
    assert gif_url('S09E06', 729604, 729605, 'xxx') == 'https://morbotron.com/gif/S09E06/729604/729605.gif?b64lines=eHh4'


def test_caption_url():
    assert caption_url('S09E06', 729604) == 'https://morbotron.com/caption?e=S09E06&t=729604'
