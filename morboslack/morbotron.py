import requests
import base64
import six
import textwrap

BASE_URL = 'https://morbotron.com'
WRAP_WIDTH = 24


class RequestFailedException(Exception):
    pass


def search(key):
    """
    Search Morbotron
    """
    res = requests.get('{}/api/search?q={}'.format(BASE_URL, key))
    if res.ok:
        return res.json()
    else:
        raise RequestFailedException()


def context_frames(episode, timestamp, before=4000, after=4000):
    """
    Get frames around the given timestamp.
    """
    url = '{base}/api/frames/{episode}/{ts}/{before}/{after}'.format(base=BASE_URL, episode=episode, ts=timestamp,
                                                                     before=before, after=after)
    res = requests.get(url)
    if res.ok:
        return res.json()
    else:
        raise RequestFailedException()


def image_url(episode, timestamp, text=''):
    """
    Return a frame URL based on an episode and timestamp.
    """
    b64 = base64.b64encode(six.b('\n'.join(textwrap.wrap(text, WRAP_WIDTH)))).decode('latin1')
    param = '?b64lines={}'.format(b64) if len(text) else ''
    return '{base}/meme/{episode}/{timestamp}.jpg{param}'.format(base=BASE_URL, episode=episode,
                                                                 timestamp=timestamp, param=param)


def gif_url(episode, start, end, text=''):
    """
    Return a GIF URL based on an episode and start and end timestamps.
    """
    b64 = base64.b64encode(six.b('\n'.join(textwrap.wrap(text, WRAP_WIDTH)))).decode('latin1')
    param = '?b64lines={}'.format(b64) if len(text) else ''
    return '{base}/gif/{episode}/{start}/{end}.gif{param}'.format(base=BASE_URL, episode=episode,
                                                                  start=start, end=end, param=param)


def thumb_url(episode, timestamp):
    """
    Return a thumbnail URL based on an episode and timestamp.
    """
    return '{base}/img/{episode}/{timestamp}/small.jpg'.format(base=BASE_URL, episode=episode, timestamp=timestamp)
