#!/usr/bin/env python3
"""
Generate roadmap dashboard HTML from roadmap.json
Feature 026 (FR-009): Roadmap visualization

This script generates a visual dashboard of the roadmap progress.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_roadmap(json_path: Path) -> dict:
    """Load roadmap JSON data."""
    with open(json_path) as f:
        return json.load(f)


def generate_html(roadmap: dict) -> str:
    """Generate HTML dashboard from roadmap data."""

    # Calculate overall progress
    total_features = len(roadmap["features"])
    completed_features = sum(1 for f in roadmap["features"] if f["status"] == "completed")
    progress_percent = (completed_features / total_features * 100) if total_features > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soundlab + D-ASE Roadmap v{roadmap["version"]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .info-card {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
        }}
        .info-card h3 {{
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        .info-card p {{
            font-size: 20px;
            color: #2c3e50;
            font-weight: bold;
        }}
        .progress-bar {{
            background: #ecf0f1;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #3498db, #2ecc71);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.3s ease;
        }}
        .phases {{
            margin: 30px 0;
        }}
        .phase {{
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .phase.completed {{ border-color: #2ecc71; }}
        .phase.active {{ border-color: #f39c12; }}
        .phase h3 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .phase-meta {{
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: #7f8c8d;
        }}
        .features {{
            margin: 30px 0;
        }}
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }}
        .feature {{
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 5px;
            background: white;
        }}
        .feature-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .feature-id {{
            font-weight: bold;
            color: #3498db;
        }}
        .status {{
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        .status.completed {{ background: #2ecc71; color: white; }}
        .status.in_progress {{ background: #f39c12; color: white; }}
        .status.planning {{ background: #3498db; color: white; }}
        .status.backlog {{ background: #95a5a6; color: white; }}
        .priority {{
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        .priority.P1 {{ background: #e74c3c; color: white; }}
        .priority.P2 {{ background: #f39c12; color: white; }}
        .priority.P3 {{ background: #95a5a6; color: white; }}
        .feature-name {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .feature-desc {{
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 10px;
        }}
        .feature-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #95a5a6;
        }}
        .milestones {{
            margin: 30px 0;
        }}
        .milestone {{
            border: 2px solid #3498db;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            background: #f8f9fa;
        }}
        .milestone.completed {{ border-color: #2ecc71; background: #d5f4e6; }}
        .milestone h3 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .milestone ul {{
            margin-left: 20px;
            margin-top: 10px;
        }}
        .milestone li {{
            margin: 5px 0;
            color: #7f8c8d;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #95a5a6;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Soundlab + D-ASE Roadmap v{roadmap["version"]}</h1>

        <div class="header-info">
            <div class="info-card">
                <h3>Status</h3>
                <p>{roadmap["status"].title()}</p>
            </div>
            <div class="info-card">
                <h3>Target Release</h3>
                <p>{roadmap["target_release"]}</p>
            </div>
            <div class="info-card">
                <h3>Last Updated</h3>
                <p>{roadmap["last_updated"]}</p>
            </div>
            <div class="info-card">
                <h3>Progress</h3>
                <p>{progress_percent:.0f}%</p>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill" style="width: {progress_percent}%">
                {completed_features}/{total_features} Features
            </div>
        </div>

        <h2>Development Phases</h2>
        <div class="phases">
"""

    # Add phases
    for phase in roadmap["phases"]:
        status_class = phase["status"]
        if phase["progress_percent"] == 100:
            status_class = "completed"
        html += f"""
            <div class="phase {status_class}">
                <h3>Phase {phase["id"]}: {phase["name"]}</h3>
                <div class="phase-meta">
                    <span>Weeks {phase["weeks"]}</span>
                    <span>Status: {phase["status"].title()}</span>
                    <span>Progress: {phase["progress_percent"]}%</span>
                </div>
            </div>
"""

    html += """
        </div>

        <h2>Features</h2>
        <div class="features">
            <div class="feature-grid">
"""

    # Add features
    for feature in roadmap["features"]:
        html += f"""
                <div class="feature">
                    <div class="feature-header">
                        <span class="feature-id">{feature["id"]}</span>
                        <span class="status {feature["status"]}">{feature["status"].replace("_", " ").title()}</span>
                    </div>
                    <div class="feature-name">{feature["name"]}</div>
                    <div class="feature-desc">{feature["description"]}</div>
                    <div class="feature-meta">
                        <span class="priority {feature["priority"]}">{feature["priority"]}</span>
                        <span>Phase {feature["phase"]}</span>
                        <span>{feature["effort_weeks"]}w effort</span>
                    </div>
                </div>
"""

    html += """
            </div>
        </div>

        <h2>Milestones</h2>
        <div class="milestones">
"""

    # Add milestones
    for milestone in roadmap["milestones"]:
        status_class = "completed" if milestone["status"] == "completed" else ""
        html += f"""
            <div class="milestone {status_class}">
                <h3>{milestone["id"]}: {milestone["name"]} (Week {milestone["week"]})</h3>
                <p><strong>Status:</strong> {milestone["status"].title()}</p>
                <p><strong>Exit Criteria:</strong></p>
                <ul>
"""
        for criterion in milestone["exit_criteria"]:
            html += f"                    <li>{criterion}</li>\n"

        html += "                </ul>\n"
        if "completed_date" in milestone:
            html += f"                <p><strong>Completed:</strong> {milestone['completed_date']}</p>\n"
        html += "            </div>\n"

    html += f"""
        </div>

        <footer>
            <p>Generated by Feature 026 roadmap dashboard</p>
            <p>Data source: <a href="roadmap.json">roadmap.json</a></p>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
        </footer>
    </div>
</body>
</html>
"""

    return html


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    roadmap_json = repo_root / "docs" / "roadmap.json"
    output_html = repo_root / "docs" / "roadmap.html"

    if not roadmap_json.exists():
        print(f"Error: {roadmap_json} not found")
        return 1

    # Load roadmap data
    roadmap = load_roadmap(roadmap_json)

    # Generate HTML
    html = generate_html(roadmap)

    # Write output
    output_html.write_text(html)

    print(f"✓ Roadmap dashboard generated: {output_html}")
    print(f"  Open file://{output_html.absolute()} in your browser")

    return 0


if __name__ == "__main__":
    sys.exit(main())
