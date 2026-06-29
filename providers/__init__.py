from .autoreisen import AutoReisenProvider
from .pluscar import PlusCarProvider


def get_providers(settings):
    return [PlusCarProvider(settings), AutoReisenProvider()]
