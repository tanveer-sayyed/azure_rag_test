"""
pytest conftest — wires OllamaModel into deepeval globally.
Imported automatically by pytest before any test module.
"""
import os
import yaml
import pytest
from deepeval.models import OllamaModel

_config_path = __file__.replace("conftest.py", "eval_config.yaml")
with open(_config_path) as _f:
    _cfg = yaml.safe_load(_f)

judge_model = OllamaModel(
    model=os.environ["OLLAMA_MODEL"],
    base_url=_cfg["judge"]["base_url"],
)

_results: list = []


@pytest.fixture
def report_collector():
    """Session-level list that accumulates per-(case, metric) result rows."""
    return _results


def pytest_sessionfinish(session, exitstatus):
    """Write collected results to reports/latest/ after the session ends."""
    if _results:
        from harness.reporter import write_report
        from harness.viz import print_table, write_html
        write_report(_results)
        print_table(_results)
        write_html(_results)
