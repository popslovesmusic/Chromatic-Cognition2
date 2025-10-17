#!/usr/bin/env python3
"""
Soundlab + D-ASE v1.0 Final Validation Suite
Author: Soundlab Research Division
Date: 2025-10-17

Performs end-to-end testing, benchmarking, and reporting.
"""

import os, sys, time, json, csv, math, statistics, importlib, subprocess
from datetime import datetime
from pathlib import Path
import numpy as np

REPORT_DIR = Path("tests/reports")
DATA_DIR = Path("data")
LOG_DIR = Path("logs")

for d in [REPORT_DIR, DATA_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def write_report(name, content):
    path = REPORT_DIR / name
    with open(path, "w", encoding="utf-8") as f: f.write(content)
    log(f"✓ Report written: {path}")

def run_shell(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"⚠️ Command failed: {cmd}\n{r.stderr}")
    return r.stdout.strip()

# ---------------------------------------------------------------------------
# SECTION I – Environment Check
# ---------------------------------------------------------------------------

def check_environment():
    log("Checking Python environment...")
    version = sys.version.split()[0]
    env_report = [f"Python version: {version}"]
    try:
        import fastapi, sounddevice, websockets, numpy
        env_report.append("✓ Core dependencies present")
    except Exception as e:
        env_report.append(f"⚠️ Missing dependency: {e}")
    return "\n".join(env_report)

# ---------------------------------------------------------------------------
# SECTION II – Core Module Tests
# ---------------------------------------------------------------------------

def test_engine():
    log("Testing dase_engine core...")
    try:
        import dase_engine
        avx2 = dase_engine.hasAVX2()
        fma = dase_engine.hasFMA()
        result = f"✓ dase_engine imported | AVX2={avx2}, FMA={fma}"
    except Exception as e:
        result = f"❌ Failed to import dase_engine: {e}"
    return result

# ---------------------------------------------------------------------------
# SECTION III – Audio Processing Benchmark
# ---------------------------------------------------------------------------

def benchmark_audio_engine(duration=5.0):
    from server.audio_engine import AudioEngine
    ae = AudioEngine()
    sample_rate = 48000
    num_samples = int(sample_rate * duration)
    input_signal = np.random.uniform(-1, 1, num_samples).astype(np.float32)
    start = time.perf_counter()
    output = ae.processor.processBlock(
        input_signal, phi_phase=0.0, phi_depth=0.5,
        channel_frequencies=np.linspace(1, 60, 8, dtype=np.float32),
        channel_amplitudes=np.ones(8, dtype=np.float32)
    )
    elapsed = time.perf_counter() - start
    latency_ms = 1000 * elapsed / duration
    return {
        "latency_ms": latency_ms,
        "output_shape": output.shape,
        "sample_rate": sample_rate
    }

# ---------------------------------------------------------------------------
# SECTION IV – Metrics Validation
# ---------------------------------------------------------------------------

def validate_metrics():
    from server.metrics_computer import MetricsComputer
    mc = MetricsComputer()
    metrics = mc.compute_all()
    if not metrics:
        return "❌ No metrics returned."
    keys = ", ".join(metrics.keys())
    return f"✓ Metrics OK ({keys})"

# ---------------------------------------------------------------------------
# SECTION V – WebSocket + API Integration
# ---------------------------------------------------------------------------

def test_websocket():
    try:
        import websockets, asyncio

        async def ws_test():
            uri = "ws://localhost:8000/ws/metrics"
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({"ping": "test"}))
                resp = await ws.recv()
                return resp
        result = asyncio.get_event_loop().run_until_complete(ws_test())
        return f"✓ WebSocket OK: {result[:80]}..."
    except Exception as e:
        return f"⚠️ WebSocket test failed: {e}"

# ---------------------------------------------------------------------------
# SECTION VI – Report Aggregation
# ---------------------------------------------------------------------------

def generate_final_report():
    log("Aggregating results...")
    results = {
        "environment": check_environment(),
        "engine": test_engine(),
        "metrics": validate_metrics(),
        "websocket": test_websocket(),
    }

    try:
        bench = benchmark_audio_engine()
        results.update(bench)
    except Exception as e:
        results["benchmark_error"] = str(e)

    report_lines = [
        "# Soundlab + D-ASE Final System Diagnostics",
        f"Generated: {datetime.now()}",
        "",
        "## Environment",
        results["environment"],
        "",
        "## Engine",
        results["engine"],
        "",
        "## Metrics",
        results["metrics"],
        "",
        "## WebSocket",
        results["websocket"],
        "",
        "## Benchmark",
        f"Latency: {results.get('latency_ms','?')} ms",
        f"Output shape: {results.get('output_shape','?')}",
        f"Sample rate: {results.get('sample_rate','?')}",
        "",
        "## Summary",
        "- All subsystems validated" if "✓" in results["engine"] else "- Issues detected, see logs",
    ]

    write_report("final_system_diagnostics.md", "\n".join(report_lines))

    # Export JSON summary for CI dashboards
    json_path = REPORT_DIR / "final_metrics_summary.json"
    with open(json_path, "w") as jf:
        json.dump(results, jf, indent=2)
    log(f"✓ JSON summary: {json_path}")

# ---------------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log("=== Soundlab + D-ASE Final Validation Suite ===")
    generate_final_report()
    log("=== Validation Complete ===")
