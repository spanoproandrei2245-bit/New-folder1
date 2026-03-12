import time
from datetime import datetime
from itertools import cycle

def lcgg(seed: int = 42):
    a = 1_664_525
    c = 1_013_904_223
    m = 2 ** 32
    x = seed % m
    while True:
        x = (a * x + c) % m
        yield x

def colorg():
    RESET = "\033[0m"
    palette = [
        ("Crimson", "\033[91m"),
        ("Lime",    "\033[92m"),
        ("Amber",   "\033[93m"),
        ("Sky",     "\033[94m"),
        ("Violet",  "\033[95m"),
        ("Aqua",    "\033[96m"),
        ("Rose",    "\033[38;5;211m"),
        ("Gold",    "\033[38;5;220m"),
    ]
    for name, code in cycle(palette):
        yield name, code, RESET

def timeoutit(iterator, timeout: float, processor):
    start = time.perf_counter()
    for index, value in enumerate(iterator):
        elapsed = time.perf_counter() - start
        if elapsed >= timeout:
            print(f"\nTimeout {timeout} - {index} chusel v {elapsed:.3f}")
            break
        processor(value, index, elapsed)

def printproc(value, index, elapsed):
    print(f"[{elapsed:6.3f}]  #{index:>5}:  {value}")

def colorproc(value, index, elapsed):
    name, code, reset = value
    date_str = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    print(f"{code}[{elapsed:6.3f}s]  iteraciya #{index:>4}  "
          f"{date_str}  !  {name}{reset}")

SEP = "─" * 62

def demo_lcg_print(timeout=1.0):
    print(SEP)
    print(f"LCG 1: print kozhne (timeout={timeout})")
    print(SEP)
    timeoutit(lcgg(seed=42), timeout, printproc)
    print()


def demo_color_cycle(timeout=1.0):
    print(SEP)
    print(f"Color 3: date + iteration +color (timeout={timeout})")
    print(SEP)
    timeoutit(colorg(), timeout, colorproc)
    print()

if __name__ == "__main__":
    T = 1.0

    demo_lcg_print(T)
    demo_color_cycle(T)