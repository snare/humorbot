import nose
from humorbot.backend import *


def setup():
    global m
    global f
    m = Morbotron()
    f = Frinkiac()


def teardown():
    pass


def test_search():
    res = m.search('do the hustle')
    assert len(res) == 36
    res = f.search("glayvin")
    assert len(res) == 36


def test_context_frames():
    res = m.context_frames('S09E06', 729604)
    assert len(res) == 38
    res = f.context_frames('S15E01', 437270)
    assert len(res) == 29


def test_captions():
    res = m.captions('S05E02', 278561)
    d = [
        {
            "Id": 155870,
            "RepresentativeTimestamp": 275224,
            "Episode": "S05E02",
            "StartTimestamp": 274432,
            "EndTimestamp": 276683,
            "Content": "( \"The Hustle\" plays )",
            "Language": "en"
        },
        {
            "Id": 155871,
            "RepresentativeTimestamp": 277727,
            "Episode": "S05E02",
            "StartTimestamp": 276725,
            "EndTimestamp": 278936,
            "Content": "♪ Do the Hustle... ♪",
            "Language": "en"
        }
    ]
    assert res == d
    res = f.captions('S15E01', 437270)
    d = [
        {
            'Language': 'en',
            'StartTimestamp': 436433,
            'EndTimestamp': 438800,
            'RepresentativeTimestamp': 437478,
            'Episode': 'S15E01',
            'Content': ' PROF. FRINK: Great glayvin in a glass!',
            'Id': 158107
        },
        {
            'Language': 'en',
            'StartTimestamp': 438800,
            'EndTimestamp': 440367,
            'RepresentativeTimestamp': 439355,
            'Episode': 'S15E01',
            'Content': 'The Nobel prize.',
            'Id': 158108
        }
    ]
    assert res == d


def test_caption_for_query():
    assert m.caption_for_query('S05E02', 278561, 'do the hustle') == '♪ Do the Hustle... ♪'
    assert m.caption_for_query('S05E02', 278561, 'the hustle') == '♪ Do the Hustle... ♪'
    assert m.caption_for_query('S05E02', 278561, 'plays') == '( "The Hustle" plays )'


def test_image_url():
    assert m.image_url('S09E06', 729604) == 'https://morbotron.com/meme/S09E06/729604.jpg'
    assert m.image_url('S09E06', 729604, 'xxx') == 'https://morbotron.com/meme/S09E06/729604.jpg?b64lines=eHh4'


def test_thumb_url():
    assert m.thumb_url('S09E06', 729604) == 'https://morbotron.com/img/S09E06/729604/small.jpg'


def test_gif_url():
    assert m.gif_url('S09E06', 729604, 729605) == 'https://morbotron.com/gif/S09E06/729604/729605.gif'
    assert m.gif_url('S09E06', 729604, 729605, 'xxx') == 'https://morbotron.com/gif/S09E06/729604/729605.gif?b64lines=eHh4'
