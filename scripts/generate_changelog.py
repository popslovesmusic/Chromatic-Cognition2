#!/usr/bin/env python3
"""
Changelog Generator - Feature 025 (FR-005)

Generates CHANGELOG.md from git commits

Usage:
    python scripts/generate_changelog.py --version 1.0.0
"""

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def get_previous_tag():
    """Get previous git tag"""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0', 'HEAD^'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits_since(since_ref=None):
    """Get commits since reference"""
    if since_ref:
        cmd = ['git', 'log', f'{since_ref}..HEAD', '--pretty=format:%H|%s|%an|%ad', '--date=short']
    else:
        cmd = ['git', 'log', '--pretty=format:%H|%s|%an|%ad', '--date=short']

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    commits = []

    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|')
        if len(parts) == 4:
            commits.append({
                'hash': parts[0][:7],
                'subject': parts[1],
                'author': parts[2],
                'date': parts[3]
            })

    return commits


def categorize_commits(commits):
    """Categorize commits by type"""
    categories = {
        'features': [],
        'fixes': [],
        'docs': [],
        'security': [],
        'performance': [],
        'tests': [],
        'other': []
    }

    for commit in commits:
        subject = commit['subject'].lower()

        if any(x in subject for x in ['implement feature', 'feat:', 'feature']):
            categories['features'].append(commit)
        elif any(x in subject for x in ['fix:', 'bugfix', 'hotfix']):
            categories['fixes'].append(commit)
        elif any(x in subject for x in ['docs:', 'documentation']):
            categories['docs'].append(commit)
        elif any(x in subject for x in ['security', 'vulnerability', 'cve']):
            categories['security'].append(commit)
        elif any(x in subject for x in ['perf:', 'performance', 'optimize']):
            categories['performance'].append(commit)
        elif any(x in subject for x in ['test:', 'tests']):
            categories['tests'].append(commit)
        else:
            categories['other'].append(commit)

    return categories


def generate_changelog(version, output_path='CHANGELOG.md'):
    """Generate changelog file"""
    prev_tag = get_previous_tag()

    changelog = []
    changelog.append(f"# Changelog - v{version}")
    changelog.append("")
    changelog.append(f"**Release Date:** {datetime.now().strftime('%Y-%m-%d')}")
    changelog.append("")

    if prev_tag:
        changelog.append(f"## Changes since {prev_tag}")
        changelog.append("")
        commits = get_commits_since(prev_tag)
    else:
        changelog.append("## Initial Release")
        changelog.append("")
        commits = get_commits_since()

    categories = categorize_commits(commits)

    # Features
    if categories['features']:
        changelog.append("### ✨ Features")
        changelog.append("")
        for commit in categories['features']:
            changelog.append(f"- {commit['subject']} ({commit['hash']})")
        changelog.append("")

    # Security
    if categories['security']:
        changelog.append("### 🔒 Security")
        changelog.append("")
        for commit in categories['security']:
            changelog.append(f"- {commit['subject']} ({commit['hash']})")
        changelog.append("")

    # Bug Fixes
    if categories['fixes']:
        changelog.append("### 🐛 Bug Fixes")
        changelog.append("")
        for commit in categories['fixes']:
            changelog.append(f"- {commit['subject']} ({commit['hash']})")
        changelog.append("")

    # Performance
    if categories['performance']:
        changelog.append("### ⚡ Performance")
        changelog.append("")
        for commit in categories['performance']:
            changelog.append(f"- {commit['subject']} ({commit['hash']})")
        changelog.append("")

    # Documentation
    if categories['docs']:
        changelog.append("### 📚 Documentation")
        changelog.append("")
        for commit in categories['docs']:
            changelog.append(f"- {commit['subject']} ({commit['hash']})")
        changelog.append("")

    # Tests
    if categories['tests']:
        changelog.append("### ✅ Tests")
        changelog.append("")
        for commit in categories['tests']:
            changelog.append(f"- {commit['subject']} ({commit['hash']})")
        changelog.append("")

    # Other changes
    if categories['other']:
        changelog.append("### 🔧 Other Changes")
        changelog.append("")
        for commit in categories['other']:
            changelog.append(f"- {commit['subject']} ({commit['hash']})")
        changelog.append("")

    # Statistics
    changelog.append("---")
    changelog.append("")
    changelog.append("### Release Statistics")
    changelog.append("")
    changelog.append(f"- **Total commits:** {len(commits)}")
    changelog.append(f"- **Features:** {len(categories['features'])}")
    changelog.append(f"- **Bug fixes:** {len(categories['fixes'])}")
    changelog.append(f"- **Security updates:** {len(categories['security'])}")
    if prev_tag:
        changelog.append(f"- **Previous version:** {prev_tag}")
    changelog.append("")

    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(changelog))

    print(f"✓ Changelog generated: {output_path}")
    print(f"  Total commits: {len(commits)}")
    print(f"  Features: {len(categories['features'])}")
    print(f"  Bug fixes: {len(categories['fixes'])}")

    return changelog


def main():
    parser = argparse.ArgumentParser(description='Generate CHANGELOG.md from git commits')

    parser.add_argument(
        '--version',
        required=True,
        help='Version number (e.g., 1.0.0)'
    )

    parser.add_argument(
        '--output',
        default='CHANGELOG.md',
        help='Output file path (default: CHANGELOG.md)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Changelog Generator - Feature 025")
    print("=" * 70)
    print()

    generate_changelog(args.version, args.output)


if __name__ == '__main__':
    main()
