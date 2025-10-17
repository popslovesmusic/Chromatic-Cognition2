"""
Privacy Manager - Feature 024 (FR-009, FR-010, FR-011)

Handles data privacy, PII redaction, retention policies, and data purging.

Requirements:
- FR-009: Structured logging with PII redaction, no raw payloads
- FR-010: Retention policy enforcement and purge CLI
- FR-011: Storage minimization, no secrets in localStorage
"""

import re
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import glob

logger = logging.getLogger(__name__)


class PIIRedactor:
    """PII redaction for logs and data (FR-009)"""

    # Regex patterns for PII detection
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b')
    IP_ADDRESS_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')

    # Fields to always redact
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'api_key', 'authorization',
        'credit_card', 'ssn', 'social_security', 'passport'
    }

    @staticmethod
    def redact_text(text: str, preserve_domain: bool = False) -> str:
        """
        Redact PII from text.

        Args:
            text: Input text
            preserve_domain: If True, keep email domains

        Returns:
            Redacted text
        """
        if not text:
            return text

        # Redact emails
        if preserve_domain:
            text = PIIRedactor.EMAIL_PATTERN.sub(
                lambda m: f"***@{m.group().split('@')[1]}",
                text
            )
        else:
            text = PIIRedactor.EMAIL_PATTERN.sub('[EMAIL]', text)

        # Redact phone numbers
        text = PIIRedactor.PHONE_PATTERN.sub('[PHONE]', text)

        # Redact SSN
        text = PIIRedactor.SSN_PATTERN.sub('[SSN]', text)

        # Redact credit cards
        text = PIIRedactor.CREDIT_CARD_PATTERN.sub('[CARD]', text)

        # Redact IP addresses (partial)
        text = PIIRedactor.IP_ADDRESS_PATTERN.sub(
            lambda m: '.'.join(m.group().split('.')[:2] + ['***', '***']),
            text
        )

        return text

    @staticmethod
    def redact_dict(data: Dict, hash_fields: bool = False) -> Dict:
        """
        Redact PII from dictionary.

        Args:
            data: Input dictionary
            hash_fields: If True, hash sensitive values instead of redacting

        Returns:
            Redacted dictionary
        """
        if not isinstance(data, dict):
            return data

        redacted = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Check if field is sensitive
            is_sensitive = any(
                sensitive in key_lower
                for sensitive in PIIRedactor.SENSITIVE_FIELDS
            )

            if is_sensitive:
                if hash_fields and isinstance(value, str):
                    # Hash instead of redact
                    redacted[key] = hashlib.sha256(value.encode()).hexdigest()[:16]
                else:
                    redacted[key] = '[REDACTED]'
            elif isinstance(value, str):
                redacted[key] = PIIRedactor.redact_text(value)
            elif isinstance(value, dict):
                redacted[key] = PIIRedactor.redact_dict(value, hash_fields)
            elif isinstance(value, list):
                redacted[key] = [
                    PIIRedactor.redact_dict(item, hash_fields)
                    if isinstance(item, dict)
                    else PIIRedactor.redact_text(str(item))
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted

    @staticmethod
    def should_log_payload(endpoint: str, method: str) -> bool:
        """
        Determine if request/response payload should be logged.

        Args:
            endpoint: API endpoint
            method: HTTP method

        Returns:
            True if payload should be logged, False otherwise
        """
        # Never log auth payloads
        if 'auth' in endpoint.lower() or 'login' in endpoint.lower():
            return False

        # Never log raw audio/binary data
        if any(x in endpoint.lower() for x in ['audio', 'upload', 'stream']):
            return False

        return True


class RetentionPolicy:
    """Data retention policy enforcement (FR-010)"""

    def __init__(self, config_path: str = 'config/privacy.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load retention policy configuration"""
        if not self.config_path.exists():
            # Default policy
            return {
                'retention_periods': {
                    'logs': 30,  # days
                    'session_metrics': 90,
                    'audit_logs': 365,
                    'temp_files': 7,
                    'recordings': 30
                },
                'auto_purge_enabled': True,
                'purge_schedule': 'daily'
            }

        with open(self.config_path) as f:
            return json.load(f)

    def get_retention_period(self, data_type: str) -> int:
        """Get retention period in days for data type"""
        return self.config['retention_periods'].get(data_type, 30)

    def is_expired(self, file_path: Path, data_type: str) -> bool:
        """Check if file has exceeded retention period"""
        retention_days = self.get_retention_period(data_type)

        if not file_path.exists():
            return False

        file_age_days = (
            datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
        ).days

        return file_age_days > retention_days

    def find_expired_files(self, data_type: str, search_pattern: str) -> List[Path]:
        """Find all expired files matching pattern"""
        expired = []

        for file_path in glob.glob(search_pattern, recursive=True):
            path = Path(file_path)
            if self.is_expired(path, data_type):
                expired.append(path)

        return expired


class PrivacyManager:
    """Privacy management and data purging (FR-010, FR-011)"""

    def __init__(self, config_path: str = 'config/privacy.json'):
        self.retention = RetentionPolicy(config_path)
        self.redactor = PIIRedactor()

    def redact_log_entry(self, entry: Dict) -> Dict:
        """Redact PII from log entry"""
        return self.redactor.redact_dict(entry, hash_fields=True)

    def should_log_payload(self, endpoint: str, method: str) -> bool:
        """Check if payload should be logged"""
        return self.redactor.should_log_payload(endpoint, method)

    def purge_expired_data(
        self,
        data_type: str,
        search_pattern: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Purge expired data files.

        Args:
            data_type: Type of data (logs, session_metrics, etc.)
            search_pattern: Glob pattern to find files
            dry_run: If True, only report what would be deleted

        Returns:
            Purge statistics
        """
        expired_files = self.retention.find_expired_files(data_type, search_pattern)

        stats = {
            'data_type': data_type,
            'files_found': len(expired_files),
            'files_deleted': 0,
            'bytes_freed': 0,
            'dry_run': dry_run,
            'deleted_files': []
        }

        for file_path in expired_files:
            try:
                file_size = file_path.stat().st_size
                stats['bytes_freed'] += file_size

                if not dry_run:
                    file_path.unlink()
                    stats['files_deleted'] += 1

                stats['deleted_files'].append({
                    'path': str(file_path),
                    'size': file_size,
                    'age_days': (
                        datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                    ).days if file_path.exists() else 0
                })

            except Exception as e:
                logger.error(f"Error purging {file_path}: {e}")

        return stats

    def purge_all_expired(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Purge all expired data based on retention policy.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Combined purge statistics
        """
        purge_targets = [
            ('logs', 'logs/**/*.log'),
            ('session_metrics', 'logs/**/*_metrics.csv'),
            ('temp_files', 'temp/**/*'),
            ('recordings', 'recordings/**/*.wav')
        ]

        results = []
        total_files = 0
        total_bytes = 0

        for data_type, pattern in purge_targets:
            stats = self.purge_expired_data(data_type, pattern, dry_run)
            results.append(stats)
            total_files += stats['files_deleted']
            total_bytes += stats['bytes_freed']

        return {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'total_files_deleted': total_files,
            'total_bytes_freed': total_bytes,
            'results': results
        }

    def audit_log_purge(self, purge_stats: Dict) -> None:
        """Create audit log entry for purge action"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'data_purge',
            'dry_run': purge_stats.get('dry_run', False),
            'files_deleted': purge_stats.get('total_files_deleted', 0),
            'bytes_freed': purge_stats.get('total_bytes_freed', 0),
            'details': purge_stats.get('results', [])
        }

        # Write to audit log
        audit_log_path = Path('logs/audit.log')
        audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(audit_log_path, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')

        logger.info(f"Purge audit logged: {audit_entry}")

    def validate_frontend_storage(self, storage_data: Dict) -> Dict:
        """
        Validate frontend localStorage data (FR-011).

        Args:
            storage_data: Frontend localStorage contents

        Returns:
            Validation report with warnings
        """
        warnings = []
        secrets_found = []

        # Check for secrets
        for key, value in storage_data.items():
            key_lower = key.lower()

            if any(s in key_lower for s in ['token', 'secret', 'password', 'key']):
                secrets_found.append(key)
                warnings.append(f"Secret found in localStorage: {key}")

        # Check data size
        total_size = sum(len(str(v)) for v in storage_data.values())
        if total_size > 5 * 1024 * 1024:  # 5MB
            warnings.append(f"localStorage exceeds 5MB: {total_size} bytes")

        return {
            'valid': len(secrets_found) == 0,
            'warnings': warnings,
            'secrets_found': secrets_found,
            'total_size_bytes': total_size,
            'recommendations': [
                'Only store preset names and non-sensitive UI state',
                'Use session storage for temporary data',
                'Never store tokens or secrets in localStorage'
            ]
        }


def create_audit_log_entry(action: str, user: str, details: Dict) -> Dict:
    """Create structured audit log entry"""
    return {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'user': user,
        'details': details,
        'correlation_id': hashlib.sha256(
            f"{action}{user}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
    }
