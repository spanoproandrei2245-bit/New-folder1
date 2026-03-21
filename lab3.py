import time
import functools
from collections import OrderedDict, defaultdict

def memoize(funktsiya, rozmir_keshu=None, polityka='lru'):
    kesh = OrderedDict()
    lichylnyk_zvertanj = defaultdict(int)
    chas_stvorennya = {}

    def _zastosuvatyEviktsiynu():
        if rozmir_keshu is None or len(kesh) < rozmir_keshu:
            return

        if polityka == 'lru':
            kesh.popitem(last=False)

        elif polityka == 'lfu':
            naymenshe_zvertanj = min(lichylnyk_zvertanj[k] for k in kesh)
            for klyuch in list(kesh.keys()):
                if lichylnyk_zvertanj[klyuch] == naymenshe_zvertanj:
                    kesh.pop(klyuch)
                    lichylnyk_zvertanj.pop(klyuch, None)
                    chas_stvorennya.pop(klyuch, None)
                    break

    @functools.wraps(funktsiya)
    def obgortka(*arhy, **kvarhy):
        klyuch_keshu = (arhy, tuple(sorted(kvarhy.items())))

        if klyuch_keshu in kesh:
            lichylnyk_zvertanj[klyuch_keshu] += 1
            if polityka == 'lru':
                kesh.move_to_end(klyuch_keshu)
            return kesh[klyuch_keshu]

        rezultat = funktsiya(*arhy, **kvarhy)

        _zastosuvatyEviktsiynu()

        kesh[klyuch_keshu] = rezultat
        lichylnyk_zvertanj[klyuch_keshu] = 1
        chas_stvorennya[klyuch_keshu] = time.time()

        return rezultat

    return obgortka