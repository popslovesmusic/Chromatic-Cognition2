#!/usr/bin/env python3
"""
Example 05: Performance Monitoring

Demonstrates performance monitoring and diagnostics:
- Monitor FPS and latency
- Track system metrics
- Analyze performance
- Generate reports

Usage:
    python examples/05_performance_monitoring.py
"""

import requests
import json
import os
import time
from typing import Dict, Any, List
from statistics import mean, stdev


class PerformanceMonitor:
    """Client for performance monitoring"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.samples: List[Dict[str, Any]] = []

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.json()

    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        response = self.session.get(f"{self.base_url}/api/status")
        response.raise_for_status()
        return response.json()

    def get_latency_metrics(self) -> Dict[str, Any]:
        """Get latency diagnostics"""
        response = self.session.get(f"{self.base_url}/api/latency/metrics")
        response.raise_for_status()
        return response.json()

    def collect_sample(self) -> Dict[str, Any]:
        """Collect a single performance sample"""
        sample = {
            'timestamp': time.time(),
            'metrics': self.get_metrics(),
            'status': self.get_status(),
        }

        try:
            sample['latency'] = self.get_latency_metrics()
        except:
            sample['latency'] = None

        self.samples.append(sample)
        return sample

    def monitor(self, duration: int = 10, interval: float = 1.0):
        """Monitor performance for specified duration"""
        print(f"Monitoring for {duration} seconds (sampling every {interval}s)...\n")

        start_time = time.time()
        sample_count = 0

        while time.time() - start_time < duration:
            sample = self.collect_sample()
            sample_count += 1

            elapsed = time.time() - start_time
            fps = sample['status'].get('fps', 0)
            frame = sample['metrics'].get('frame', 0)
            ici = sample['metrics'].get('ici', 0)
            criticality = sample['metrics'].get('criticality', 0)

            print(f"[{elapsed:6.1f}s] Sample {sample_count:3d} | "
                  f"FPS: {fps:5.1f} | "
                  f"Frame: {frame:6d} | "
                  f"ICI: {ici:6.3f} | "
                  f"Crit: {criticality:6.3f}")

            time.sleep(interval)

        print(f"\n✓ Collected {len(self.samples)} samples")

    def analyze(self) -> Dict[str, Any]:
        """Analyze collected samples"""
        if not self.samples:
            return {}

        # Extract FPS values
        fps_values = [s['status'].get('fps', 0) for s in self.samples]

        # Extract ICI values
        ici_values = [s['metrics'].get('ici', 0) for s in self.samples]

        # Extract criticality values
        crit_values = [s['metrics'].get('criticality', 0) for s in self.samples]

        # Extract latency if available
        latency_values = []
        for s in self.samples:
            if s.get('latency') and 'total_latency_ms' in s['latency']:
                latency_values.append(s['latency']['total_latency_ms'])

        analysis = {
            'sample_count': len(self.samples),
            'duration': self.samples[-1]['timestamp'] - self.samples[0]['timestamp'],
            'fps': {
                'mean': mean(fps_values) if fps_values else 0,
                'min': min(fps_values) if fps_values else 0,
                'max': max(fps_values) if fps_values else 0,
                'stdev': stdev(fps_values) if len(fps_values) > 1 else 0,
            },
            'ici': {
                'mean': mean(ici_values) if ici_values else 0,
                'min': min(ici_values) if ici_values else 0,
                'max': max(ici_values) if ici_values else 0,
                'stdev': stdev(ici_values) if len(ici_values) > 1 else 0,
            },
            'criticality': {
                'mean': mean(crit_values) if crit_values else 0,
                'min': min(crit_values) if crit_values else 0,
                'max': max(crit_values) if crit_values else 0,
                'stdev': stdev(crit_values) if len(crit_values) > 1 else 0,
            }
        }

        if latency_values:
            analysis['latency_ms'] = {
                'mean': mean(latency_values),
                'min': min(latency_values),
                'max': max(latency_values),
                'stdev': stdev(latency_values) if len(latency_values) > 1 else 0,
            }

        return analysis

    def print_report(self, analysis: Dict[str, Any]):
        """Print performance analysis report"""
        print("\n" + "=" * 70)
        print("Performance Analysis Report")
        print("=" * 70)

        print(f"\nSamples: {analysis['sample_count']}")
        print(f"Duration: {analysis['duration']:.2f}s")

        print("\nFPS (Frames Per Second):")
        print(f"  Mean:   {analysis['fps']['mean']:6.2f}")
        print(f"  Min:    {analysis['fps']['min']:6.2f}")
        print(f"  Max:    {analysis['fps']['max']:6.2f}")
        print(f"  StdDev: {analysis['fps']['stdev']:6.2f}")

        print("\nICI (Inter-Channel Interference):")
        print(f"  Mean:   {analysis['ici']['mean']:6.3f}")
        print(f"  Min:    {analysis['ici']['min']:6.3f}")
        print(f"  Max:    {analysis['ici']['max']:6.3f}")
        print(f"  StdDev: {analysis['ici']['stdev']:6.3f}")

        print("\nCriticality:")
        print(f"  Mean:   {analysis['criticality']['mean']:6.3f}")
        print(f"  Min:    {analysis['criticality']['min']:6.3f}")
        print(f"  Max:    {analysis['criticality']['max']:6.3f}")
        print(f"  StdDev: {analysis['criticality']['stdev']:6.3f}")

        if 'latency_ms' in analysis:
            print("\nLatency (ms):")
            print(f"  Mean:   {analysis['latency_ms']['mean']:6.2f}")
            print(f"  Min:    {analysis['latency_ms']['min']:6.2f}")
            print(f"  Max:    {analysis['latency_ms']['max']:6.2f}")
            print(f"  StdDev: {analysis['latency_ms']['stdev']:6.2f}")

        # Performance assessment
        print("\nPerformance Assessment:")
        fps_mean = analysis['fps']['mean']
        if fps_mean >= 30:
            print("  FPS: ✓ EXCELLENT (≥30 Hz)")
        elif fps_mean >= 20:
            print("  FPS: ⚠ ACCEPTABLE (≥20 Hz)")
        else:
            print("  FPS: ✗ POOR (<20 Hz)")

        if 'latency_ms' in analysis:
            latency_mean = analysis['latency_ms']['mean']
            if latency_mean <= 50:
                print("  Latency: ✓ EXCELLENT (≤50ms)")
            elif latency_mean <= 100:
                print("  Latency: ⚠ ACCEPTABLE (≤100ms)")
            else:
                print("  Latency: ✗ HIGH (>100ms)")

        print("=" * 70)


def main():
    """Main example"""
    print("=" * 70)
    print("Soundlab Performance Monitoring Example")
    print("=" * 70)

    # Get server URL from environment or use default
    server_url = os.getenv('SOUNDLAB_API_URL', 'http://localhost:8000')
    print(f"\nConnecting to: {server_url}\n")

    # Create monitor
    monitor = PerformanceMonitor(server_url)

    try:
        # Monitor for 10 seconds
        monitor.monitor(duration=10, interval=1.0)

        # Analyze results
        analysis = monitor.analyze()

        # Print report
        monitor.print_report(analysis)

        # Save report to file
        report_file = "performance_report.json"
        with open(report_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"\n✓ Report saved to: {report_file}")

    except requests.ConnectionError:
        print(f"\n✗ Error: Could not connect to {server_url}")
        print("Make sure the server is running: cd server && python main.py")
    except requests.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


if __name__ == "__main__":
    main()
