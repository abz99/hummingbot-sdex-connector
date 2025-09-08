"""
Stellar QA Metrics Collection and Integration
Integrates QA framework with monitoring system for real-time quality metrics.
"""

import asyncio
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .stellar_logging import get_stellar_logger, LogCategory
from .stellar_metrics import get_stellar_metrics, StellarMetrics


class QAMetricType(Enum):
    """Types of QA metrics collected."""

    COVERAGE = "coverage"
    TEST_SUCCESS = "test_success"
    CODE_QUALITY = "code_quality"
    COMPLIANCE = "compliance"
    SECURITY = "security"


@dataclass
class QAMetricResult:
    """Result of a QA metric collection."""

    metric_type: QAMetricType
    module: str
    value: float
    metadata: Dict[str, Any]
    timestamp: float
    success: bool = True
    error_message: Optional[str] = None


class StellarQAMetricsCollector:
    """Collects and reports QA metrics to the monitoring system."""

    def __init__(self, metrics: Optional[StellarMetrics] = None):
        """Initialize QA metrics collector."""
        self.logger = get_stellar_logger()
        self.metrics = metrics or get_stellar_metrics()
        self.project_root = self._find_project_root()

        # Critical modules requiring higher coverage thresholds
        self.critical_modules = {
            "stellar_security_manager": 95.0,
            "stellar_chain_interface": 90.0,
            "stellar_network_manager": 90.0,
            "stellar_order_manager": 90.0,
            "stellar_exchange": 85.0,
            "stellar_soroban_manager": 85.0,
            "stellar_security": 95.0,
        }

        # QA requirements from quality catalogue
        self.qa_requirements = {
            "test_coverage": 80.0,
            "critical_coverage": 90.0,
            "test_success_rate": 95.0,
            "code_quality_score": 80.0,
            "security_compliance": 90.0,
        }

        self.logger.info(
            "QA metrics collector initialized",
            category=LogCategory.METRICS,
            critical_modules_count=len(self.critical_modules),
            project_root=str(self.project_root),
        )

    async def initialize(self) -> bool:
        """Initialize the QA metrics collector."""
        try:
            # Verify project structure
            if not self.project_root.exists():
                self.logger.error(f"Project root not found: {self.project_root}")
                return False

            # Initialize Stellar metrics connection
            self.stellar_metrics = get_stellar_metrics()

            self.logger.info(
                "QA metrics collector initialized successfully",
                category=LogCategory.METRICS,
                project_root=str(self.project_root),
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to initialize QA metrics collector: {str(e)}",
                category=LogCategory.METRICS,
                error=str(e),
            )
            return False

    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "setup.py").exists() or (current / "pyproject.toml").exists():
                return current
            if (current / ".git").exists():
                return current
            current = current.parent
        return Path.cwd()

    async def collect_all_qa_metrics(self) -> List[QAMetricResult]:
        """Collect all QA metrics and update monitoring system."""
        results = []

        try:
            # Collect coverage metrics
            coverage_results = await self.collect_coverage_metrics()
            results.extend(coverage_results)

            # Collect test execution metrics
            test_results = await self.collect_test_execution_metrics()
            results.extend(test_results)

            # Collect code quality metrics
            quality_results = await self.collect_code_quality_metrics()
            results.extend(quality_results)

            # Collect compliance metrics
            compliance_results = await self.collect_compliance_metrics()
            results.extend(compliance_results)

            # Update monitoring system
            await self.update_monitoring_metrics(results)

            self.logger.info(
                f"Collected {len(results)} QA metrics",
                category=LogCategory.METRICS,
                results_count=len(results),
                successful_metrics=sum(1 for r in results if r.success),
            )

        except Exception as e:
            self.logger.error(
                f"Failed to collect QA metrics: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return results

    async def collect_coverage_metrics(self) -> List[QAMetricResult]:
        """Collect test coverage metrics."""
        results = []

        try:
            # Run coverage collection
            coverage_data = await self._get_coverage_data()

            if not coverage_data:
                self.logger.warning("No coverage data available", category=LogCategory.QA)
                return results

            # Process overall coverage
            overall_coverage = coverage_data.get("total_coverage", 0.0)
            results.append(
                QAMetricResult(
                    metric_type=QAMetricType.COVERAGE,
                    module="overall",
                    value=overall_coverage,
                    metadata={"type": "line_coverage"},
                    timestamp=time.time(),
                )
            )

            # Process module-specific coverage
            for module, coverage in coverage_data.get("modules", {}).items():
                results.append(
                    QAMetricResult(
                        metric_type=QAMetricType.COVERAGE,
                        module=module,
                        value=coverage,
                        metadata={"type": "line_coverage"},
                        timestamp=time.time(),
                    )
                )

                # Check if this is a critical module
                if module in self.critical_modules:
                    threshold = self.critical_modules[module]
                    results.append(
                        QAMetricResult(
                            metric_type=QAMetricType.COVERAGE,
                            module=module,
                            value=coverage,
                            metadata={"type": "critical_coverage", "threshold": threshold},
                            timestamp=time.time(),
                            success=coverage >= threshold,
                        )
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to collect coverage metrics: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return results

    async def collect_test_execution_metrics(self) -> List[QAMetricResult]:
        """Collect test execution metrics."""
        results = []

        try:
            # Run pytest with json reporting
            test_data = await self._get_test_execution_data()

            if not test_data:
                return results

            # Calculate success rate
            total_tests = test_data.get("total", 0)
            passed_tests = test_data.get("passed", 0)
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

            results.append(
                QAMetricResult(
                    metric_type=QAMetricType.TEST_SUCCESS,
                    module="overall",
                    value=success_rate,
                    metadata={
                        "total_tests": total_tests,
                        "passed_tests": passed_tests,
                        "failed_tests": test_data.get("failed", 0),
                        "skipped_tests": test_data.get("skipped", 0),
                    },
                    timestamp=time.time(),
                )
            )

            # Per-suite metrics
            for suite, suite_data in test_data.get("test_suites", {}).items():
                suite_total = suite_data.get("total", 0)
                suite_passed = suite_data.get("passed", 0)
                suite_success_rate = (suite_passed / suite_total * 100) if suite_total > 0 else 0

                results.append(
                    QAMetricResult(
                        metric_type=QAMetricType.TEST_SUCCESS,
                        module=suite,
                        value=suite_success_rate,
                        metadata=suite_data,
                        timestamp=time.time(),
                    )
                )

        except Exception as e:
            self.logger.error(
                f"Failed to collect test execution metrics: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return results

    async def collect_code_quality_metrics(self) -> List[QAMetricResult]:
        """Collect code quality metrics from static analysis."""
        results = []

        try:
            # Run flake8 for code quality
            quality_data = await self._get_code_quality_data()

            for module, quality_info in quality_data.items():
                # Calculate quality score (lower violation count = higher score)
                violations = quality_info.get("violations", 0)
                lines_of_code = quality_info.get("lines_of_code", 1)
                violation_rate = violations / lines_of_code
                quality_score = max(0, 100 - (violation_rate * 100))

                results.append(
                    QAMetricResult(
                        metric_type=QAMetricType.CODE_QUALITY,
                        module=module,
                        value=quality_score,
                        metadata=quality_info,
                        timestamp=time.time(),
                    )
                )

        except Exception as e:
            self.logger.error(
                f"Failed to collect code quality metrics: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return results

    async def collect_compliance_metrics(self) -> List[QAMetricResult]:
        """Collect compliance metrics from QA requirements."""
        results = []

        try:
            # Load quality catalogue
            compliance_data = await self._get_compliance_data()

            for category, compliance_info in compliance_data.items():
                compliance_percentage = compliance_info.get("compliance_percentage", 0.0)
                priority = compliance_info.get("priority", "medium")

                results.append(
                    QAMetricResult(
                        metric_type=QAMetricType.COMPLIANCE,
                        module=category,
                        value=compliance_percentage,
                        metadata={"priority": priority, **compliance_info},
                        timestamp=time.time(),
                    )
                )

        except Exception as e:
            self.logger.error(
                f"Failed to collect compliance metrics: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return results

    async def update_monitoring_metrics(self, results: List[QAMetricResult]):
        """Update the monitoring system with collected QA metrics."""

        for result in results:
            try:
                if result.metric_type == QAMetricType.COVERAGE:
                    if result.metadata.get("type") == "critical_coverage":
                        self.metrics.update_critical_module_coverage(
                            result.module, result.value, "critical"
                        )
                    else:
                        self.metrics.update_test_coverage(result.module, result.value, "line")

                elif result.metric_type == QAMetricType.TEST_SUCCESS:
                    self.metrics.update_test_success_rate(result.module, result.value, "unit")

                elif result.metric_type == QAMetricType.CODE_QUALITY:
                    self.metrics.update_code_quality_score(
                        result.module, result.value, "violations"
                    )

                elif result.metric_type == QAMetricType.COMPLIANCE:
                    priority = result.metadata.get("priority", "medium")
                    self.metrics.update_requirements_compliance(
                        result.module, result.value, priority
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to update monitoring metric for {result.module}: {e}",
                    category=LogCategory.ERROR_HANDLING,
                    module=result.module,
                    metric_type=result.metric_type.value,
                    error=str(e),
                )

    async def _get_coverage_data(self) -> Dict[str, Any]:
        """Get coverage data from pytest-cov."""
        try:
            # Run coverage command
            cmd = [
                "python",
                "-m",
                "pytest",
                "--cov=hummingbot/connector/exchange/stellar",
                "--cov-report=json:coverage.json",
                "--tb=no",
                "-q",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            # Read coverage JSON file
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, "r") as f:
                    coverage_data = json.load(f)

                # Process coverage data
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0.0)
                modules = {}

                for file_path, file_data in coverage_data.get("files", {}).items():
                    if "stellar" in file_path:
                        module_name = Path(file_path).stem
                        modules[module_name] = file_data.get("summary", {}).get(
                            "percent_covered", 0.0
                        )

                return {
                    "total_coverage": total_coverage,
                    "modules": modules,
                    "raw_data": coverage_data,
                }

        except Exception as e:
            self.logger.error(
                f"Failed to get coverage data: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return {}

    async def _get_test_execution_data(self) -> Dict[str, Any]:
        """Get test execution data from pytest."""
        try:
            # Run pytest with json output
            cmd = [
                "python",
                "-m",
                "pytest",
                "--json-report",
                "--json-report-file=test_report.json",
                "test/",
                "--tb=no",
                "-q",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            # Read test report JSON
            report_file = self.project_root / "test_report.json"
            if report_file.exists():
                with open(report_file, "r") as f:
                    test_data = json.load(f)

                summary = test_data.get("summary", {})

                return {
                    "total": summary.get("total", 0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "skipped": summary.get("skipped", 0),
                    "duration": test_data.get("duration", 0.0),
                    "test_suites": self._process_test_suites(test_data),
                }

        except Exception as e:
            self.logger.error(
                f"Failed to get test execution data: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return {}

    async def _get_code_quality_data(self) -> Dict[str, Any]:
        """Get code quality data from static analysis."""
        quality_data = {}

        try:
            # Run flake8 for code quality
            stellar_path = self.project_root / "hummingbot/connector/exchange/stellar"

            for python_file in stellar_path.glob("*.py"):
                if python_file.name.startswith("__"):
                    continue

                module_name = python_file.stem

                # Count lines of code
                with open(python_file, "r") as f:
                    lines = [
                        line for line in f if line.strip() and not line.strip().startswith("#")
                    ]
                    lines_of_code = len(lines)

                # Run flake8 on file
                cmd = ["flake8", "--count", str(python_file)]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                # Parse violations count
                violations = 0
                if stdout:
                    lines = stdout.decode().strip().split("\n")
                    for line in lines:
                        if line and line[-1].isdigit():
                            violations = int(line.split()[-1])
                            break

                quality_data[module_name] = {
                    "violations": violations,
                    "lines_of_code": lines_of_code,
                    "file_path": str(python_file),
                }

        except Exception as e:
            self.logger.error(
                f"Failed to get code quality data: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return quality_data

    async def _get_compliance_data(self) -> Dict[str, Any]:
        """Get compliance data from QA requirements."""
        compliance_data = {}

        try:
            # Load quality catalogue
            qa_catalogue_file = self.project_root / "qa/quality_catalogue.json"
            if qa_catalogue_file.exists():
                with open(qa_catalogue_file, "r") as f:
                    qa_data = json.load(f)

                # Calculate compliance for each requirement category
                requirements = qa_data.get("requirements", [])

                categories = {}
                for req in requirements:
                    category = req.get("category", "unknown")
                    priority = req.get("priority", "medium")

                    if category not in categories:
                        categories[category] = {"total": 0, "completed": 0, "priority": priority}

                    categories[category]["total"] += 1
                    if req.get("status") == "completed":
                        categories[category]["completed"] += 1

                # Calculate compliance percentages
                for category, data in categories.items():
                    compliance_percentage = (
                        (data["completed"] / data["total"] * 100) if data["total"] > 0 else 0
                    )
                    compliance_data[category] = {
                        "compliance_percentage": compliance_percentage,
                        "priority": data["priority"],
                        "total_requirements": data["total"],
                        "completed_requirements": data["completed"],
                    }

        except Exception as e:
            self.logger.error(
                f"Failed to get compliance data: {e}",
                category=LogCategory.ERROR_HANDLING,
                error=str(e),
            )

        return compliance_data

    def _process_test_suites(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process test data by test suite."""
        test_suites = {}

        for test in test_data.get("tests", []):
            nodeid = test.get("nodeid", "")
            outcome = test.get("outcome", "unknown")

            # Extract test suite name from nodeid
            if "::" in nodeid:
                suite_name = nodeid.split("::")[0].split("/")[-1].replace(".py", "")
            else:
                suite_name = "unknown"

            if suite_name not in test_suites:
                test_suites[suite_name] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

            test_suites[suite_name]["total"] += 1
            test_suites[suite_name][outcome] = test_suites[suite_name].get(outcome, 0) + 1

        return test_suites


# Global QA metrics collector instance
_qa_metrics_collector: Optional[StellarQAMetricsCollector] = None


def get_qa_metrics_collector() -> StellarQAMetricsCollector:
    """Get or create global QA metrics collector."""
    global _qa_metrics_collector
    if _qa_metrics_collector is None:
        _qa_metrics_collector = StellarQAMetricsCollector()
    return _qa_metrics_collector


async def collect_and_update_qa_metrics() -> List[QAMetricResult]:
    """Convenience function to collect and update all QA metrics."""
    collector = get_qa_metrics_collector()
    return await collector.collect_all_qa_metrics()
