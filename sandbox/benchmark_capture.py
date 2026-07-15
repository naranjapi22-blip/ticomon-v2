# ruff: noqa: E402

from __future__ import annotations

import gc
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rendering.capture_animation import CaptureAnimation

# =====================================
# CONFIGURATION
# =====================================

RUNS = 20
WARMUP = 3

SPRITE = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev/regular/25.gif"

POKEMON = "Pikachu"
TYPE_NAME = "electric"
POKEBALL = "Poké Ball"

# =====================================


@dataclass
class Result:

    render_ms: float
    encode_ms: float
    total_ms: float
    memory_mb: float
    gif_size_kb: float


def create_animation():

    return CaptureAnimation(
        sprite_path=SPRITE,
        pokemon_name=POKEMON,
        pokeball=POKEBALL,
        captured=True,
        type_name=TYPE_NAME,
    )


def benchmark_once() -> Result:

    gc.collect()

    tracemalloc.start()

    animation = create_animation()

    total_start = time.perf_counter()

    render_start = time.perf_counter()
    animation.render()
    render_ms = (time.perf_counter() - render_start) * 1000

    encode_start = time.perf_counter()
    gif = animation.gif_bytes()
    encode_ms = (time.perf_counter() - encode_start) * 1000

    total_ms = (time.perf_counter() - total_start) * 1000

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    gif.seek(0, 2)
    gif_size = gif.tell() / 1024

    return Result(
        render_ms,
        encode_ms,
        total_ms,
        peak / (1024 * 1024),
        gif_size,
    )


def average(values):
    return statistics.mean(values)


def report(results):

    render = [r.render_ms for r in results]
    encode = [r.encode_ms for r in results]
    total = [r.total_ms for r in results]
    memory = [r.memory_mb for r in results]
    size = [r.gif_size_kb for r in results]

    print()
    print("=" * 60)
    print("CAPTURE ANIMATION BENCHMARK")
    print("=" * 60)

    print(f"Python      : {sys.version.split()[0]}")
    print(f"Runs        : {len(results)}")
    print()

    print(f"Render Avg  : {average(render):8.2f} ms")
    print(f"Encode Avg  : {average(encode):8.2f} ms")
    print(f"Total Avg   : {average(total):8.2f} ms")
    print()

    print(f"Fastest     : {min(total):8.2f} ms")
    print(f"Slowest     : {max(total):8.2f} ms")
    print(f"Median      : {statistics.median(total):8.2f} ms")
    print(f"Std Dev     : {statistics.stdev(total):8.2f} ms")
    print()

    print(f"Peak RAM    : {average(memory):8.2f} MB")
    print(f"GIF Size    : {average(size):8.2f} KB")

    render_pct = average(render) / average(total) * 100
    encode_pct = average(encode) / average(total) * 100

    print()
    print(f"Render %    : {render_pct:6.2f}%")
    print(f"Encode %    : {encode_pct:6.2f}%")
    print("=" * 60)


def main():

    print()
    print("Warmup...")

    for _ in range(WARMUP):
        benchmark_once()

    print("OK\n")

    results = []

    for i in range(RUNS):

        r = benchmark_once()

        results.append(r)

        print(
            f"[{i+1:02}/{RUNS}] "
            f"Render={r.render_ms:7.2f} ms | "
            f"Encode={r.encode_ms:7.2f} ms | "
            f"Total={r.total_ms:7.2f} ms"
        )

    report(results)


if __name__ == "__main__":
    main()
