import time
import functools
from collections import OrderedDict, defaultdict


def memoize(funktsiya, rozmir_keshu=None, polityka='lru', chas_zhyttya=None, svoya_polityka=None):
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

        if svoya_polityka is not None:
            klyuch_dlya_vydalennya = svoya_polityka(kesh, lichylnyk_zvertanj, chas_stvorennya)
            if klyuch_dlya_vydalennya is not None:
                kesh.pop(klyuch_dlya_vydalennya, None)
                lichylnyk_zvertanj.pop(klyuch_dlya_vydalennya, None)
                chas_stvorennya.pop(klyuch_dlya_vydalennya, None)
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

    def ochystyty_kesh():
        kesh.clear()
        lichylnyk_zvertanj.clear()
        chas_stvorennya.clear()

    def status_keshu():
        return {
            'rozmir': len(kesh),
            'maksymalnyy_rozmir': rozmir_keshu,
            'polityka': polityka if svoya_polityka is None else 'svoya',
            'klyuchi': list(kesh.keys()),
            'zvernannya': dict(lichylnyk_zvertanj),
        }

    obgortka.ochystyty_kesh = ochystyty_kesh
    obgortka.status_keshu = status_keshu

    return obgortka

def dekorator_memoize(rozmir_keshu=None, polityka='lru', chas_zhyttya=None, svoya_polityka=None):
    def dekorator(funktsiya):
        return memoize(funktsiya, rozmir_keshu=rozmir_keshu, polityka=polityka,
                       chas_zhyttya=chas_zhyttya, svoya_polityka=svoya_polityka)
    return dekorator

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def faktorial(n):
    if n == 0:
        return 1
    return n * faktorial(n - 1)

def povil_ne_zvedennya(osnova, stepen):
    time.sleep(0.05)
    return osnova ** stepen

if __name__ == '__main__':
    print("Демонстрація мемоізації")
    print("\nLRU (розмір кешу = 4)")
    memo_fib = memoize(fibonacci, rozmir_keshu=4, polityka='lru')

    for n in [10, 20, 10, 30, 20, 40]:
        pochatkovyy_chas = time.perf_counter()
        res = memo_fib(n)
        elapsed = time.perf_counter() - pochatkovyy_chas
        print(f"fibonacci({n:2d}) = {res:<10} [{elapsed*1000:.3f} мс]")

    print(f"Статус кешу: {memo_fib.status_keshu()['rozmir']} записів")

    print("\nLFU (розмір кешу = 3)")
    memo_fact = memoize(faktorial, rozmir_keshu=3, polityka='lfu')

    for n in [5, 5, 5, 3, 3, 7, 9]:
        res = memo_fact(n)
        print(f"  faktorial({n}) = {res}")

    st = memo_fact.status_keshu()
    print(f"Залишилось у кеші: {st['klyuchi']}")
    print(f"Частота звертань: {st['zvernannya']}")

    print("\nTTL (lifetime = 0.3 с)")
    memo_zv = memoize(povil_ne_zvedennya, polityka='ttl', chas_zhyttya=0.3)

    t0 = time.perf_counter()
    print(f"  2^10 = {memo_zv(2, 10)}  [{(time.perf_counter()-t0)*1000:.1f} мс]  (перший виклик)")
    t0 = time.perf_counter()
    print(f"  2^10 = {memo_zv(2, 10)}  [{(time.perf_counter()-t0)*1000:.1f} мс]  (з кешу)")
    time.sleep(0.35)
    t0 = time.perf_counter()
    print(f"  2^10 = {memo_zv(2, 10)}  [{(time.perf_counter()-t0)*1000:.1f} мс]  (після TTL - перерахунок)")

    print("\nСвоя політика")

    def svoya_eviktsiya(kesh, lichylnyk, chas_st):
        return max(kesh.keys(), key=lambda k: len(str(k)), default=None)

    @dekorator_memoize(rozmir_keshu=2, svoya_polityka=svoya_eviktsiya)
    def suma(*chysla):
        return sum(chysla)

    print(f"suma(1,2,3) = {suma(1, 2, 3)}")
    print(f"suma(4,5,6,7,8) = {suma(4, 5, 6, 7, 8)}")
    print(f"suma(1) = {suma(1)}")
    print(f"Кеш: {suma.status_keshu()['klyuchi']}")

    print("\nОчищення кешу")
    print(f"Розмір до очищення: {memo_fib.status_keshu()['rozmir']}")
    memo_fib.ochystyty_kesh()
    print(f"Розмір після очищення: {memo_fib.status_keshu()['rozmir']}")

    print("\n" + "=" * 55)