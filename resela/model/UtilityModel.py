from urllib.parse import urlparse, urljoin
from flask import request


def is_safe_url(target):
    """Assure that the redirect target is a safe URL.

    The URL is deemed safe if it will lead to the same server.

    :param target: URL of the target of the redirection.
    :type target: str
    """

    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc