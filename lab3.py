import time
import functools
from collections import OrderedDict, defaultdict

def memoize(funktsiya, rozmir_keshu=None):
    kesh = OrderedDict()
    lichylnyk_zvertanj = defaultdict(int)

    @functools.wraps(funktsiya)
    def obgortka(*arhy, **kvarhy):
        klyuch_keshu = (arhy, tuple(sorted(kvarhy.items())))

        if klyuch_keshu in kesh:
            lichylnyk_zvertanj[klyuch_keshu] += 1
            return kesh[klyuch_keshu]

        rezultat = funktsiya(*arhy, **kvarhy)

        kesh[klyuch_keshu] = rezultat
        lichylnyk_zvertanj[klyuch_keshu] = 1

        return rezultat

    return obgortka