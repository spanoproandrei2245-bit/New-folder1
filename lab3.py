import time
import functools
from collections import OrderedDict, defaultdict

def memoize(funktsiya, rozmir_keshu=None, polityka='lru', chas_zhyttya=None):
    kesh = OrderedDict()
    lichylnyk_zvertanj = defaultdict(int)
    chas_stvorennya = {}

    def _vydalyty_zastarily():
        if chas_zhyttya is None:
            return
        potochnyy_chas = time.time()
        klyuchi_dlya_vydalennya = [
            klyuch for klyuch, chas in chas_stvorennya.items()
            if potochnyy_chas - chas > chas_zhyttya
        ]
        for klyuch in klyuchi_dlya_vydalennya:
            kesh.pop(klyuch, None)
            lichylnyk_zvertanj.pop(klyuch, None)
            chas_stvorennya.pop(klyuch, None)

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

        elif polityka == 'ttl':
            if kesh:
                najstarshyy = min(chas_stvorennya, key=chas_stvorennya.get)
                kesh.pop(najstarshyy, None)
                lichylnyk_zvertanj.pop(najstarshyy, None)
                chas_stvorennya.pop(najstarshyy, None)

    @functools.wraps(funktsiya)
    def obgortka(*arhy, **kvarhy):
        _vydalyty_zastarily()

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