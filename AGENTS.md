AGENTS.md

Project: Soundlab + D-ASE Consciousness Architecture
Purpose: Define agent responsibilities, interfaces, and development phases for autonomous code generation, testing, and integration.

1. Agent Overview
Agent	Role	Primary Files	Dependencies
A-001 Core Compiler	Maintains and builds all C++ sources (analog_universal_node_engine_avx2.*, chromatic_field_processor.*, python_bindings.cpp). Handles pybind11 builds.	cpp/, setup.py, build.sh	pybind11, AVX2 CPU
A-002 Python Bridge	Manages Python bindings and server modules (soundlab_server.py, phi_modulator.py, audio_engine.py).	server/	sounddevice, FastAPI
A-003 WebSocket Controller	Implements /ws/ui, /ws/metrics, /ws/sync, and playback channels. Handles JSON messaging.	server/main.py	asyncio, uvicorn
A-004 Frontend Renderer	Generates and maintains static HTML/CSS/JS UI (control matrix, Φ-matrix dashboard, metrics HUD).	static/	WebSocket API
A-005 Preset Manager	Controls localStorage, preset save/load/export logic.	static/js/preset-browser.js	A-003 WebSocket
A-006 Metrics Analyzer	Computes and streams ICI, coherence, criticality, and state classification.	server/ici_engine.py, state_classifier.py	NumPy, SciPy
A-007 Auto-Φ Controller	Performs adaptive modulation (Auto-Φ Learner + Criticality Balancer).	server/auto_phi.py, criticality_balancer.py	Metrics Analyzer
A-008 Predictive Engine	Predicts next consciousness state and controls early adjustments.	server/predictive_model.py	A-006, A-007
A-009 Recorder	Captures synchronized audio, metrics, and control logs.	server/session_recorder.py	A-002, A-003
A-010 Timeline Player	Provides playback and scrubbing of recorded sessions.	server/timeline_player.py	Recorder output
A-011 Data Exporter	Converts session data to CSV, JSON, HDF5, MP4.	server/data_exporter.py	Recorder
A-012 Cluster Monitor	Aggregates node telemetry, manages roles, health, and drift.	server/cluster_monitor.py	PhaseNet
A-013 Hardware Interface	Bridges I²S/GPIO hardware nodes and hybrid DSP units.	hardware/	PySerial, microcontroller firmware
A-014 Knowledge Agent	Manages docs, feature specs, tests, and code generation plans.	docs/, tests/	All agents
2. Communication Topology

WebSocket Bus:
/ws/ui → control updates
/ws/metrics → metrics stream
/ws/cluster → node telemetry
/ws/playback → timeline replay

REST Endpoints:
/api/record/*, /api/export, /api/cluster/*, /api/node/*

Shared Storage:
/sessions/ (recordings)
/state/ (persistent config)
/logs/ (audit + runtime logs)

3. Build + Test Workflow

A-001 builds C++ → Python extension (dase_engine.so).

A-002/A-003 start Python server and verify /ws/ui echo tests.

A-004 runs frontend smoke test (controls visible, connected).

A-006–A-008 compute metrics, learning loops verified under 5 ms latency.

A-009–A-011 record/export sessions; run regression test battery.

A-012–A-013 simulate cluster + hardware integration.

A-014 updates docs, specs, and changelogs.

4. Coding Guidelines

Use Python 3.11+, C++17, and pybind11 for bindings.

Maintain deterministic float precision (single precision across modules).

Max end-to-end latency: <10 ms audio, <100 ms UI.

Follow feature spec numbers (###-feature-name) in branch naming.

Every module must include: self_test(), docstring header, and log output.

5. Agent Lifecycle Commands
Action	Description
plan <feature>	Retrieve related spec and generate implementation outline.
build <module>	Compile or assemble current module.
test <module>	Execute defined tests from tests/ or inline self-tests.
report	Summarize status and dependencies.
handoff	Commit changes and notify dependent agents.
6. Versioning and Docs

Feature tracking: FEATURES.md

Specs: /docs/specs/###-*.md

Agents update CHANGELOG.md automatically on merge.

Unit tests logged under /tests/reports/.