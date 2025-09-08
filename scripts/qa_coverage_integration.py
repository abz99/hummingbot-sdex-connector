#!/usr/bin/env python3
"""
QA Coverage Integration Script

Integrates coverage data from check_critical_coverage.py with the monitoring system
via stellar_qa_metrics.py to provide real-time QA metrics to Grafana.

QA_ID: REQ-TEST-004, REQ-MONITOR-003

Usage:
    python scripts/qa_coverage_integration.py --coverage-file=coverage.xml
    python scripts/qa_coverage_integration.py --continuous --interval=300
"""

import sys
import asyncio
import argparse
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from scripts.check_critical_coverage import CriticalCoverageChecker
    from hummingbot.connector.exchange.stellar.stellar_qa_metrics import (
        StellarQAMetricsCollector,
        QAMetricResult,
        QAMetricType
    )
    from hummingbot.connector.exchange.stellar.stellar_metrics import StellarMetrics
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QACoverageIntegrator:
    """Integrates coverage checking with monitoring system."""
    
    def __init__(self, 
                 coverage_file: str = "coverage.xml",
                 metrics_update_interval: float = 60.0):
        self.coverage_file = coverage_file
        self.metrics_update_interval = metrics_update_interval
        
        # Initialize components
        self.coverage_checker = None
        self.qa_metrics_collector = None
        self.stellar_metrics = None
        
        # Integration state
        self.last_coverage_data = {}
        self.last_update_time = None
        
    async def initialize(self) -> bool:
        """Initialize all components."""
        try:
            # Initialize coverage checker
            if Path(self.coverage_file).exists():
                self.coverage_checker = CriticalCoverageChecker(self.coverage_file)
                logger.info(f"Initialized coverage checker with file: {self.coverage_file}")
            else:
                logger.warning(f"Coverage file not found: {self.coverage_file}")
                return False
            
            # Initialize QA metrics collector
            self.qa_metrics_collector = StellarQAMetricsCollector()
            await self.qa_metrics_collector.initialize()
            logger.info("Initialized QA metrics collector")
            
            # Initialize Stellar metrics (for direct updates)
            self.stellar_metrics = StellarMetrics()
            logger.info("Initialized Stellar metrics")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    async def collect_and_integrate_coverage(self) -> bool:
        """Collect coverage data and integrate with monitoring system."""
        try:
            if not self.coverage_checker:
                logger.error("Coverage checker not initialized")
                return False
            
            # Parse coverage data
            coverage_data = self.coverage_checker.parse_coverage_xml()
            logger.debug(f"Parsed coverage data for {len(coverage_data)} modules")
            
            # Check critical coverage
            all_passed, passed_modules, failed_modules, warnings = self.coverage_checker.check_critical_coverage()
            
            # Log results
            logger.info(f"Coverage check results: {len(passed_modules)} passed, {len(failed_modules)} failed")
            if warnings:
                logger.warning(f"Coverage warnings: {warnings}")
            
            # Update monitoring metrics
            await self._update_monitoring_metrics(coverage_data, all_passed, passed_modules, failed_modules)
            
            # Store for comparison
            self.last_coverage_data = coverage_data
            self.last_update_time = datetime.now(timezone.utc)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to collect and integrate coverage: {e}")
            return False
    
    async def _update_monitoring_metrics(self,
                                       coverage_data: Dict[str, float],
                                       all_passed: bool,
                                       passed_modules: List[str], 
                                       failed_modules: List[str]):
        """Update monitoring system with coverage metrics."""
        
        # Calculate overall coverage
        if coverage_data:
            overall_coverage = sum(coverage_data.values()) / len(coverage_data)
            
            # Update overall coverage metric
            self.stellar_metrics.update_test_coverage(
                module="overall",
                coverage_type="overall", 
                coverage_percentage=overall_coverage
            )
            logger.debug(f"Updated overall coverage: {overall_coverage:.1f}%")
        
        # Update individual module coverage
        for module_name, coverage_percentage in coverage_data.items():
            # Determine if this is a critical module
            is_critical = module_name in self.coverage_checker.CRITICAL_MODULES
            coverage_type = "critical" if is_critical else "standard"
            
            self.stellar_metrics.update_test_coverage(
                module=module_name,
                coverage_type=coverage_type,
                coverage_percentage=coverage_percentage
            )
            
            # Update critical module coverage specifically
            if is_critical:
                required_threshold = self.coverage_checker.CRITICAL_MODULES[module_name]
                self.stellar_metrics.update_critical_module_coverage(
                    module=module_name,
                    coverage_percentage=coverage_percentage,
                    threshold_type="critical"
                )
        
        # Update compliance status based on critical modules
        compliance_percentage = 100.0 if all_passed else (50.0 if passed_modules else 0.0)
        self.stellar_metrics.update_requirements_compliance(
            requirement_category="coverage",
            compliance_percentage=compliance_percentage,
            priority="critical"
        )
        
        # Update QA collector with results
        if self.qa_metrics_collector:
            qa_results = []
            
            # Add coverage results
            for module_name, coverage_percentage in coverage_data.items():
                qa_results.append(QAMetricResult(
                    metric_type=QAMetricType.COVERAGE,
                    module=module_name,
                    value=coverage_percentage,
                    timestamp=time.time(),
                    metadata={
                        "coverage_type": "critical" if module_name in self.coverage_checker.CRITICAL_MODULES else "standard"
                    }
                ))
            
            # Add overall compliance result
            qa_results.append(QAMetricResult(
                metric_type=QAMetricType.COMPLIANCE,
                module="critical_modules",
                value=compliance_percentage,
                timestamp=time.time(),
                metadata={
                    "passed_modules": len(passed_modules),
                    "failed_modules": len(failed_modules),
                    "total_critical_modules": len(self.coverage_checker.CRITICAL_MODULES)
                }
            ))
            
            # Update monitoring system
            await self.qa_metrics_collector.update_monitoring_metrics(qa_results)
            logger.debug(f"Updated monitoring system with {len(qa_results)} QA results")
    
    async def run_continuous_monitoring(self, interval_seconds: int = 300):
        """Run continuous coverage monitoring."""
        logger.info(f"Starting continuous coverage monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                start_time = time.time()
                
                # Check if coverage file has been updated
                coverage_file_path = Path(self.coverage_file)
                if coverage_file_path.exists():
                    file_mtime = coverage_file_path.stat().st_mtime
                    
                    # Only update if file has changed or it's been a while
                    should_update = (
                        self.last_update_time is None or
                        file_mtime > self.last_update_time.timestamp() or
                        (datetime.now(timezone.utc) - self.last_update_time).total_seconds() > interval_seconds
                    )
                    
                    if should_update:
                        success = await self.collect_and_integrate_coverage()
                        if success:
                            logger.info("Successfully updated coverage metrics")
                        else:
                            logger.error("Failed to update coverage metrics")
                    else:
                        logger.debug("Coverage file unchanged, skipping update")
                else:
                    logger.warning(f"Coverage file not found: {self.coverage_file}")
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval_seconds - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in continuous monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)  # Wait before retrying
    
    async def run_single_update(self) -> bool:
        """Run a single coverage update."""
        logger.info("Running single coverage update")
        
        success = await self.collect_and_integrate_coverage()
        if success:
            logger.info("Coverage integration completed successfully")
            
            # Print summary
            if self.last_coverage_data:
                overall_coverage = sum(self.last_coverage_data.values()) / len(self.last_coverage_data)
                logger.info(f"Overall coverage: {overall_coverage:.1f}%")
                logger.info(f"Modules processed: {len(self.last_coverage_data)}")
        else:
            logger.error("Coverage integration failed")
        
        return success
    
    def generate_integration_report(self) -> str:
        """Generate integration status report."""
        lines = [
            "# QA Coverage Integration Report",
            f"Generated at: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Configuration",
            f"- Coverage file: {self.coverage_file}",
            f"- Metrics update interval: {self.metrics_update_interval}s",
            "",
            "## Component Status"
        ]
        
        # Component status
        lines.append(f"- Coverage Checker: {'✅ Active' if self.coverage_checker else '❌ Not initialized'}")
        lines.append(f"- QA Metrics Collector: {'✅ Active' if self.qa_metrics_collector else '❌ Not initialized'}")
        lines.append(f"- Stellar Metrics: {'✅ Active' if self.stellar_metrics else '❌ Not initialized'}")
        
        # Last update info
        if self.last_update_time:
            lines.extend([
                "",
                "## Last Update",
                f"- Timestamp: {self.last_update_time.isoformat()}",
                f"- Modules processed: {len(self.last_coverage_data)}",
            ])
            
            if self.last_coverage_data:
                overall_coverage = sum(self.last_coverage_data.values()) / len(self.last_coverage_data)
                lines.append(f"- Overall coverage: {overall_coverage:.1f}%")
        
        return "\n".join(lines)

async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate coverage data with QA monitoring system"
    )
    parser.add_argument(
        '--coverage-file',
        type=str,
        default='coverage.xml',
        help='Path to coverage XML file (default: coverage.xml)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run in continuous monitoring mode'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Update interval in seconds for continuous mode (default: 300)'
    )
    parser.add_argument(
        '--report-file',
        type=str,
        help='Output integration status report to file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize integrator
        integrator = QACoverageIntegrator(
            coverage_file=args.coverage_file,
            metrics_update_interval=args.interval
        )
        
        # Initialize components
        if not await integrator.initialize():
            logger.error("Failed to initialize QA coverage integrator")
            sys.exit(1)
        
        if args.continuous:
            # Run continuous monitoring
            await integrator.run_continuous_monitoring(args.interval)
        else:
            # Run single update
            success = await integrator.run_single_update()
            
            # Generate report if requested
            if args.report_file:
                report = integrator.generate_integration_report()
                report_path = Path(args.report_file)
                report_path.write_text(report, encoding='utf-8')
                logger.info(f"Integration report saved to: {report_path}")
            
            # Exit with appropriate code
            sys.exit(0 if success else 1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())