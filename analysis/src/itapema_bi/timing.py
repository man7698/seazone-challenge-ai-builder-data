"""Medicao real (nao estimada) de tempo de execucao e pico de memoria por etapa.

Pico de memoria e amostrado via psutil (RSS do processo) por uma thread em
background a cada 20ms enquanto a etapa roda - mede o processo inteiro, incluindo
memoria nativa alocada por Polars/DuckDB (que tracemalloc nao veria, por so
rastrear alocacoes do interpretador Python).
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass

import psutil

_PROCESS = psutil.Process()


@dataclass
class StepReport:
    name: str
    seconds: float
    peak_rss_mb: float
    start_rss_mb: float


REPORTS: list[StepReport] = []


@contextmanager
def measure(name: str):
    start_rss = _PROCESS.memory_info().rss
    peak = [start_rss]
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            peak[0] = max(peak[0], _PROCESS.memory_info().rss)
            stop.wait(0.02)

    t = threading.Thread(target=sampler, daemon=True)
    t.start()
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        stop.set()
        t.join()
        peak[0] = max(peak[0], _PROCESS.memory_info().rss)
        report = StepReport(
            name=name,
            seconds=elapsed,
            peak_rss_mb=peak[0] / (1024 * 1024),
            start_rss_mb=start_rss / (1024 * 1024),
        )
        REPORTS.append(report)
        print(f"[{name}] {elapsed:.2f}s | pico RSS {report.peak_rss_mb:.0f} MB")


def summary_markdown() -> str:
    lines = ["| Etapa | Tempo (s) | Pico RSS (MB) |", "|---|---|---|"]
    for r in REPORTS:
        lines.append(f"| {r.name} | {r.seconds:.2f} | {r.peak_rss_mb:.0f} |")
    total = sum(r.seconds for r in REPORTS)
    lines.append(f"| **total** | **{total:.2f}** | |")
    return "\n".join(lines)
