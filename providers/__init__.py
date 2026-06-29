from .autoreisen import AutoReisenProvider
from .cicar import CicarProvider
from .pluscar import PlusCarProvider


def get_providers(settings):
    return [PlusCarProvider(settings), AutoReisenProvider(), CicarProvider()]
