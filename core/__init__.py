"""Core analysis engine (in-process, no server).

parser → privacy → analyzer (Claude) → jurisdiction → benchmarks →
playbook → report_writer. All modules share the Pydantic models in
``core.models`` as the single source of truth.
"""
