from .autoreisen import AutoReisenProvider
from .cicar import CicarProvider
from .payless import PaylessProvider
from .pluscar import PlusCarProvider


def get_providers(settings):
    return [PlusCarProvider(settings), AutoReisenProvider(), CicarProvider(), PaylessProvider(settings)]
