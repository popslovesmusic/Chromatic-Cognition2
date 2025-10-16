"""
Data Exporter - Feature 019
Export and convert recorded sessions to various formats for research, visualization, or publication.

Supported Formats:
- CSV: Metrics only (simple spreadsheet format)
- JSON: Raw logs (all data streams)
- HDF5: Hierarchical compressed dataset (NumPy/MATLAB compatible)
- MP4: Audio + visual overlay (video format)

Features:
- Time-range clipping
- ZIP compression for download packages
- Checksum verification
- Compatible with external tools (NumPy, MATLAB, Audacity)

Requirements:
- FR-001: DataExporter class
- FR-002: Session folder input (Feature 017 format)
- FR-003: CSV, JSON, HDF5, MP4 export formats
- FR-004: Time-range clipping
- FR-005: REST API endpoint /api/export
- FR-007: ZIP compression

Success Criteria:
- SC-001: ±1 frame alignment
- SC-002: Export time <2× real-time
- SC-003: File integrity checksum
- SC-004: External tool compatibility
"""

import json
import csv
import wave
import os
import time
import hashlib
import zipfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np


class ExportFormat(Enum):
    """Export format options (FR-003)"""
    CSV = "csv"
    JSON = "json"
    HDF5 = "hdf5"
    MP4 = "mp4"


@dataclass
class ExportConfig:
    """Configuration for data exporter"""
    output_dir: str = "exports"
    enable_compression: bool = True  # ZIP compression (FR-007)
    enable_checksum: bool = True  # File integrity verification (SC-003)
    enable_logging: bool = True


@dataclass
class ExportRequest:
    """Export request parameters (FR-005)"""
    session_path: str
    format: ExportFormat
    output_name: Optional[str] = None
    time_range: Optional[Tuple[float, float]] = None  # (start, end) in seconds (FR-004)
    compress: bool = True  # ZIP compression


class DataExporter:
    """
    Data Exporter for recorded sessions (Feature 019)

    Exports session data to various formats for analysis and publication.
    Supports time-range clipping, compression, and checksum verification.
    """

    def __init__(self, config: Optional[ExportConfig] = None):
        """
        Initialize Data Exporter

        Args:
            config: Export configuration
        """
        self.config = config or ExportConfig()

        # Ensure output directory exists
        os.makedirs(self.config.output_dir, exist_ok=True)

        # Export statistics
        self.total_exports = 0
        self.last_export_time = 0.0
        self.last_error: Optional[str] = None

        if self.config.enable_logging:
            print("[DataExporter] Initialized")

    def export_session(self, request: ExportRequest) -> Dict[str, Any]:
        """
        Export session to specified format (FR-001, FR-002)

        Args:
            request: Export request with session path, format, and options

        Returns:
            Export result with file path, size, checksum, and metadata
        """
        start_time = time.perf_counter()

        try:
            # Validate session exists
            if not os.path.exists(request.session_path):
                raise ValueError(f"Session not found: {request.session_path}")

            # Load session metadata
            session_info = self._load_session_info(request.session_path)

            # Generate output filename
            if request.output_name:
                output_name = request.output_name
            else:
                session_name = os.path.basename(request.session_path)
                output_name = f"{session_name}_{request.format.value}"

            # Export based on format (FR-003)
            if request.format == ExportFormat.CSV:
                output_file = self._export_csv(request, output_name, session_info)
            elif request.format == ExportFormat.JSON:
                output_file = self._export_json(request, output_name, session_info)
            elif request.format == ExportFormat.HDF5:
                output_file = self._export_hdf5(request, output_name, session_info)
            elif request.format == ExportFormat.MP4:
                output_file = self._export_mp4(request, output_name, session_info)
            else:
                raise ValueError(f"Unsupported format: {request.format}")

            # Compress to ZIP if requested (FR-007)
            if request.compress:
                output_file = self._compress_to_zip(output_file, output_name)

            # Calculate checksum (SC-003)
            checksum = None
            if self.config.enable_checksum:
                checksum = self._calculate_checksum(output_file)

            # Get file size
            file_size = os.path.getsize(output_file)

            # Record statistics
            export_time = time.perf_counter() - start_time
            self.last_export_time = export_time
            self.total_exports += 1

            # Calculate real-time ratio (SC-002)
            session_duration = session_info.get('duration', 0)
            realtime_ratio = export_time / session_duration if session_duration > 0 else 0

            if self.config.enable_logging:
                print(f"[DataExporter] Exported {request.format.value} in {export_time:.2f}s "
                      f"({realtime_ratio:.2f}x real-time), size={file_size / 1024:.1f} KB")

            return {
                "ok": True,
                "output_file": output_file,
                "file_size": file_size,
                "checksum": checksum,
                "export_time": export_time,
                "realtime_ratio": realtime_ratio,
                "session_duration": session_duration,
                "time_range": request.time_range,
                "format": request.format.value
            }

        except Exception as e:
            self.last_error = str(e)
            if self.config.enable_logging:
                print(f"[DataExporter] ERROR: {e}")
            return {
                "ok": False,
                "error": str(e)
            }

    def _load_session_info(self, session_path: str) -> Dict[str, Any]:
        """
        Load session metadata (FR-002)

        Args:
            session_path: Path to session folder

        Returns:
            Session metadata dictionary
        """
        session_json = os.path.join(session_path, "session.json")

        if os.path.exists(session_json):
            with open(session_json, 'r') as f:
                return json.load(f)
        else:
            # No metadata file, create basic info
            return {
                "session_name": os.path.basename(session_path),
                "duration": 0,
                "start_time": 0
            }

    def _load_jsonl_data(self, jsonl_path: str, time_range: Optional[Tuple[float, float]] = None) -> List[Dict]:
        """
        Load JSONL data file with optional time-range clipping (FR-004, SC-001)

        Args:
            jsonl_path: Path to JSONL file
            time_range: Optional (start, end) time range in seconds

        Returns:
            List of data frames
        """
        data = []

        if not os.path.exists(jsonl_path):
            return data

        with open(jsonl_path, 'r') as f:
            for line in f:
                if line.strip():
                    frame = json.loads(line)

                    # Apply time range filter (FR-004)
                    if time_range:
                        timestamp = frame.get('timestamp', 0)
                        start, end = time_range
                        if timestamp < start or timestamp > end:
                            continue

                    data.append(frame)

        return data

    def _export_csv(self, request: ExportRequest, output_name: str, session_info: Dict) -> str:
        """
        Export session to CSV format (metrics only) (FR-003)

        Args:
            request: Export request
            output_name: Output filename base
            session_info: Session metadata

        Returns:
            Path to exported CSV file
        """
        output_file = os.path.join(self.config.output_dir, f"{output_name}.csv")

        # Load metrics data
        metrics_path = os.path.join(request.session_path, "metrics.jsonl")
        metrics_data = self._load_jsonl_data(metrics_path, request.time_range)

        if not metrics_data:
            raise ValueError("No metrics data found in session")

        # Extract all unique field names
        fieldnames = set()
        for frame in metrics_data:
            fieldnames.update(frame.keys())
        fieldnames = sorted(list(fieldnames))

        # Write CSV (SC-004: compatible with Excel, NumPy, etc.)
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(metrics_data)

        return output_file

    def _export_json(self, request: ExportRequest, output_name: str, session_info: Dict) -> str:
        """
        Export session to JSON format (raw logs, all streams) (FR-003)

        Args:
            request: Export request
            output_name: Output filename base
            session_info: Session metadata

        Returns:
            Path to exported JSON file
        """
        output_file = os.path.join(self.config.output_dir, f"{output_name}.json")

        # Load all data streams
        metrics_path = os.path.join(request.session_path, "metrics.jsonl")
        phi_path = os.path.join(request.session_path, "phi.jsonl")
        controls_path = os.path.join(request.session_path, "controls.jsonl")

        metrics_data = self._load_jsonl_data(metrics_path, request.time_range)
        phi_data = self._load_jsonl_data(phi_path, request.time_range)
        controls_data = self._load_jsonl_data(controls_path, request.time_range)

        # Create unified JSON structure
        export_data = {
            "session_info": session_info,
            "time_range": request.time_range,
            "export_timestamp": time.time(),
            "data": {
                "metrics": metrics_data,
                "phi": phi_data,
                "controls": controls_data
            }
        }

        # Write JSON
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        return output_file

    def _export_hdf5(self, request: ExportRequest, output_name: str, session_info: Dict) -> str:
        """
        Export session to HDF5 format (hierarchical compressed) (FR-003, SC-004)

        Compatible with NumPy, MATLAB, and other scientific tools.

        Args:
            request: Export request
            output_name: Output filename base
            session_info: Session metadata

        Returns:
            Path to exported HDF5 file
        """
        output_file = os.path.join(self.config.output_dir, f"{output_name}.h5")

        try:
            import h5py
        except ImportError:
            raise ImportError("h5py not installed. Install with: pip install h5py")

        # Load all data streams
        metrics_path = os.path.join(request.session_path, "metrics.jsonl")
        phi_path = os.path.join(request.session_path, "phi.jsonl")
        controls_path = os.path.join(request.session_path, "controls.jsonl")
        audio_path = os.path.join(request.session_path, "audio.wav")

        metrics_data = self._load_jsonl_data(metrics_path, request.time_range)
        phi_data = self._load_jsonl_data(phi_path, request.time_range)
        controls_data = self._load_jsonl_data(controls_path, request.time_range)

        # Create HDF5 file (SC-004: MATLAB/NumPy compatible)
        with h5py.File(output_file, 'w') as f:
            # Store session metadata
            meta_group = f.create_group('metadata')
            for key, value in session_info.items():
                meta_group.attrs[key] = value
            if request.time_range:
                meta_group.attrs['time_range_start'] = request.time_range[0]
                meta_group.attrs['time_range_end'] = request.time_range[1]

            # Store metrics as datasets
            if metrics_data:
                metrics_group = f.create_group('metrics')
                # Convert to columnar format for efficient access
                metric_arrays = self._jsonl_to_arrays(metrics_data)
                for key, values in metric_arrays.items():
                    metrics_group.create_dataset(key, data=values, compression='gzip')

            # Store phi parameters
            if phi_data:
                phi_group = f.create_group('phi')
                phi_arrays = self._jsonl_to_arrays(phi_data)
                for key, values in phi_arrays.items():
                    phi_group.create_dataset(key, data=values, compression='gzip')

            # Store controls
            if controls_data:
                controls_group = f.create_group('controls')
                controls_arrays = self._jsonl_to_arrays(controls_data)
                for key, values in controls_arrays.items():
                    controls_group.create_dataset(key, data=values, compression='gzip')

            # Store audio data (if time range specified, clip it)
            if os.path.exists(audio_path):
                audio_data, sample_rate = self._load_audio_data(audio_path, request.time_range)
                audio_group = f.create_group('audio')
                audio_group.create_dataset('data', data=audio_data, compression='gzip')
                audio_group.attrs['sample_rate'] = sample_rate
                audio_group.attrs['channels'] = audio_data.shape[1] if len(audio_data.shape) > 1 else 1

        return output_file

    def _export_mp4(self, request: ExportRequest, output_name: str, session_info: Dict) -> str:
        """
        Export session to MP4 format (audio + visual overlay) (FR-003)

        Requires ffmpeg to be installed on the system.

        Args:
            request: Export request
            output_name: Output filename base
            session_info: Session metadata

        Returns:
            Path to exported MP4 file
        """
        output_file = os.path.join(self.config.output_dir, f"{output_name}.mp4")

        # Check if ffmpeg is available
        import shutil
        if not shutil.which('ffmpeg'):
            raise RuntimeError("ffmpeg not found. Please install ffmpeg to export MP4.")

        # For now, create a placeholder implementation
        # Full implementation would require:
        # 1. Generate visualization frames from metrics data
        # 2. Combine with audio using ffmpeg
        # 3. Apply time range clipping

        # Simplified: Just copy audio and add basic metadata
        audio_path = os.path.join(request.session_path, "audio.wav")

        if not os.path.exists(audio_path):
            raise ValueError("No audio data found in session")

        # Use ffmpeg to convert WAV to MP4 with AAC audio
        import subprocess

        # Apply time range if specified (FR-004)
        if request.time_range:
            start, end = request.time_range
            duration = end - start
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start),
                '-t', str(duration),
                '-i', audio_path,
                '-c:a', 'aac',
                '-b:a', '192k',
                output_file
            ]
        else:
            cmd = [
                'ffmpeg', '-y',
                '-i', audio_path,
                '-c:a', 'aac',
                '-b:a', '192k',
                output_file
            ]

        subprocess.run(cmd, capture_output=True, check=True)

        return output_file

    def _load_audio_data(self, audio_path: str, time_range: Optional[Tuple[float, float]] = None) -> Tuple[np.ndarray, int]:
        """
        Load audio data with optional time-range clipping (FR-004)

        Args:
            audio_path: Path to WAV file
            time_range: Optional (start, end) time range in seconds

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        with wave.open(audio_path, 'rb') as wav:
            sample_rate = wav.getframerate()
            n_channels = wav.getnchannels()
            n_frames = wav.getnframes()

            # Apply time range clipping (FR-004, SC-001)
            if time_range:
                start, end = time_range
                start_frame = int(start * sample_rate)
                end_frame = int(end * sample_rate)

                # Clamp to valid range
                start_frame = max(0, min(start_frame, n_frames))
                end_frame = max(start_frame, min(end_frame, n_frames))

                # Seek to start position
                wav.setpos(start_frame)

                # Read frames
                n_frames_to_read = end_frame - start_frame
                audio_bytes = wav.readframes(n_frames_to_read)
            else:
                audio_bytes = wav.readframes(n_frames)

            # Convert to numpy array
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

            # Reshape to (frames, channels)
            if n_channels > 1:
                audio_data = audio_data.reshape(-1, n_channels)

            return audio_data, sample_rate

    def _jsonl_to_arrays(self, data: List[Dict]) -> Dict[str, np.ndarray]:
        """
        Convert JSONL data to columnar numpy arrays (SC-004: NumPy compatible)

        Args:
            data: List of data frames

        Returns:
            Dictionary of field name -> numpy array
        """
        if not data:
            return {}

        # Collect all fields
        fields = set()
        for frame in data:
            fields.update(frame.keys())

        # Convert to arrays
        arrays = {}
        for field in fields:
            values = []
            for frame in data:
                value = frame.get(field)
                # Convert to numeric if possible
                if isinstance(value, (int, float)):
                    values.append(value)
                elif isinstance(value, str):
                    # Keep strings as is (will be stored as variable-length strings in HDF5)
                    values.append(value)
                else:
                    # Convert to string representation
                    values.append(str(value) if value is not None else '')

            # Create numpy array
            if all(isinstance(v, (int, float)) for v in values):
                arrays[field] = np.array(values, dtype=np.float64)
            else:
                # Variable-length strings
                arrays[field] = np.array(values, dtype=object)

        return arrays

    def _compress_to_zip(self, file_path: str, archive_name: str) -> str:
        """
        Compress file to ZIP archive (FR-007)

        Args:
            file_path: Path to file to compress
            archive_name: Base name for archive

        Returns:
            Path to ZIP file
        """
        zip_path = os.path.join(self.config.output_dir, f"{archive_name}.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, os.path.basename(file_path))

        # Remove original file
        os.remove(file_path)

        return zip_path

    def _calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA256 checksum for file integrity (SC-003)

        Args:
            file_path: Path to file

        Returns:
            SHA256 checksum hex string
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get export statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_exports": self.total_exports,
            "last_export_time": self.last_export_time,
            "last_error": self.last_error
        }

    def list_exports(self) -> List[Dict[str, Any]]:
        """
        List all exported files in output directory

        Returns:
            List of export file info
        """
        exports = []

        if not os.path.exists(self.config.output_dir):
            return exports

        for filename in os.listdir(self.config.output_dir):
            file_path = os.path.join(self.config.output_dir, filename)
            if os.path.isfile(file_path):
                exports.append({
                    "filename": filename,
                    "size": os.path.getsize(file_path),
                    "modified": os.path.getmtime(file_path),
                    "path": file_path
                })

        return exports


# Self-test
if __name__ == "__main__":
    print("=" * 60)
    print("Data Exporter Self-Test")
    print("=" * 60)

    # Create test configuration
    config = ExportConfig(
        output_dir="test_exports",
        enable_compression=True,
        enable_checksum=True,
        enable_logging=True
    )

    exporter = DataExporter(config)

    print("\n1. Testing initialization...")
    print("   OK: Initialization")

    print("\n2. Testing statistics...")
    stats = exporter.get_statistics()
    print(f"   OK: Statistics (total_exports={stats['total_exports']})")

    print("\n3. Testing list exports...")
    exports = exporter.list_exports()
    print(f"   OK: List exports ({len(exports)} files)")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)
    print("Note: Full export testing requires recorded session")
