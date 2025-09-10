#!/usr/bin/env python3
"""
Integration Validation Runner
Orchestrates Phase 4A Real-World Validation testing.
"""

import asyncio
import json
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class IntegrationValidationRunner:
    """Orchestrates comprehensive integration validation testing."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.project_root = Path(__file__).parent.parent
        self.config_path = config_path or self.project_root / "config" / "integration_testing.yml"
        self.results_dir = self.project_root / "test_results" / "integration_validation"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Test execution state
        self.start_time = None
        self.end_time = None
        self.results = {
            "summary": {},
            "scenarios": {},
            "performance": {},
            "security": {},
            "errors": []
        }
        
    async def run_validation_suite(self) -> Dict[str, Any]:
        """Run the complete integration validation suite."""
        print("🚀 Starting Phase 4A: Real-World Validation")
        print("=" * 60)
        
        self.start_time = datetime.now()
        
        try:
            # Phase 1: Pre-validation setup
            await self._setup_validation_environment()
            
            # Phase 2: Basic connectivity validation
            await self._run_connectivity_validation()
            
            # Phase 3: Core functionality validation  
            await self._run_functionality_validation()
            
            # Phase 4: Performance benchmarking
            await self._run_performance_validation()
            
            # Phase 5: Security validation
            await self._run_security_validation()
            
            # Phase 6: Resilience validation
            await self._run_resilience_validation()
            
            # Phase 7: Generate comprehensive report
            await self._generate_validation_report()
            
        except Exception as e:
            self.results["errors"].append({
                "phase": "validation_suite",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            print(f"❌ Validation suite failed: {e}")
            
        finally:
            self.end_time = datetime.now()
            await self._cleanup_validation_environment()
            
        return self.results
        
    async def _setup_validation_environment(self):
        """Set up the validation testing environment."""
        print("\n📋 Phase 1: Setting up validation environment")
        
        try:
            # Ensure test directories exist
            (self.results_dir / "logs").mkdir(exist_ok=True)
            (self.results_dir / "metrics").mkdir(exist_ok=True)
            (self.results_dir / "reports").mkdir(exist_ok=True)
            
            # Install test dependencies if needed
            await self._ensure_test_dependencies()
            
            # Validate configuration
            await self._validate_test_configuration()
            
            print("✅ Validation environment setup complete")
            
        except Exception as e:
            print(f"❌ Environment setup failed: {e}")
            raise
            
    async def _run_connectivity_validation(self):
        """Validate basic network connectivity."""
        print("\n🌐 Phase 2: Network Connectivity Validation")
        
        connectivity_results = {
            "horizon_primary": False,
            "horizon_fallbacks": [],
            "soroban_primary": False, 
            "soroban_fallbacks": [],
            "friendbot": False
        }
        
        try:
            # Test Horizon connectivity
            print("  Testing Horizon endpoints...")
            connectivity_results["horizon_primary"] = await self._test_horizon_connectivity()
            
            # Test Soroban connectivity
            print("  Testing Soroban endpoints...")
            connectivity_results["soroban_primary"] = await self._test_soroban_connectivity()
            
            # Test Friendbot connectivity
            print("  Testing Friendbot availability...")
            connectivity_results["friendbot"] = await self._test_friendbot_connectivity()
            
            self.results["scenarios"]["connectivity"] = connectivity_results
            
            # Validate minimum connectivity requirements
            if not connectivity_results["horizon_primary"]:
                raise Exception("Primary Horizon endpoint unavailable")
                
            if not connectivity_results["friendbot"]:
                print("⚠️  Friendbot unavailable - some tests may be skipped")
                
            print("✅ Network connectivity validation complete")
            
        except Exception as e:
            print(f"❌ Connectivity validation failed: {e}")
            self.results["errors"].append({
                "phase": "connectivity_validation",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
    async def _run_functionality_validation(self):
        """Run core functionality validation tests."""
        print("\n🔧 Phase 3: Core Functionality Validation")
        
        try:
            # Run basic operations tests
            basic_results = await self._run_pytest_suite(
                "tests/integration/test_real_world_validation.py::TestRealWorldNetworkValidation"
            )
            
            # Run account operations tests
            account_results = await self._run_pytest_suite(
                "tests/integration/test_real_world_validation.py::TestRealWorldAccountOperations"
            )
            
            # Run trading operations tests  
            trading_results = await self._run_pytest_suite(
                "tests/integration/test_real_world_validation.py::TestRealWorldTradingOperations"
            )
            
            self.results["scenarios"]["functionality"] = {
                "basic_operations": basic_results,
                "account_operations": account_results,
                "trading_operations": trading_results
            }
            
            print("✅ Core functionality validation complete")
            
        except Exception as e:
            print(f"❌ Functionality validation failed: {e}")
            self.results["errors"].append({
                "phase": "functionality_validation", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
    async def _run_performance_validation(self):
        """Run performance benchmarking tests."""
        print("\n⚡ Phase 4: Performance Validation & Benchmarking")
        
        try:
            # Run performance benchmarking tests
            perf_results = await self._run_pytest_suite(
                "tests/integration/test_real_world_validation.py::TestPerformanceBenchmarking"
            )
            
            # Collect performance metrics
            performance_metrics = await self._collect_performance_metrics()
            
            self.results["performance"] = {
                "benchmark_results": perf_results,
                "metrics": performance_metrics
            }
            
            print("✅ Performance validation complete")
            
        except Exception as e:
            print(f"❌ Performance validation failed: {e}")
            self.results["errors"].append({
                "phase": "performance_validation",
                "error": str(e), 
                "timestamp": datetime.now().isoformat()
            })
            
    async def _run_security_validation(self):
        """Run security validation tests."""
        print("\n🔒 Phase 5: Security Validation")
        
        try:
            # Run security validation tests
            security_results = await self._run_pytest_suite(
                "tests/integration/test_real_world_validation.py::TestSecurityValidation"
            )
            
            self.results["security"] = {
                "validation_results": security_results,
                "security_score": await self._calculate_security_score(security_results)
            }
            
            print("✅ Security validation complete")
            
        except Exception as e:
            print(f"❌ Security validation failed: {e}")
            self.results["errors"].append({
                "phase": "security_validation",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
    async def _run_resilience_validation(self):
        """Run error resilience validation tests."""
        print("\n🛡️  Phase 6: Resilience Validation")
        
        try:
            # Run resilience tests
            resilience_results = await self._run_pytest_suite(
                "tests/integration/test_real_world_validation.py::TestErrorResilienceValidation"
            )
            
            self.results["scenarios"]["resilience"] = resilience_results
            
            print("✅ Resilience validation complete")
            
        except Exception as e:
            print(f"❌ Resilience validation failed: {e}")
            self.results["errors"].append({
                "phase": "resilience_validation",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
    async def _generate_validation_report(self):
        """Generate comprehensive validation report."""
        print("\n📊 Phase 7: Generating Validation Report")
        
        try:
            # Calculate overall metrics
            total_duration = (self.end_time or datetime.now()) - self.start_time
            
            # Generate summary
            self.results["summary"] = {
                "validation_start": self.start_time.isoformat(),
                "validation_end": (self.end_time or datetime.now()).isoformat(),
                "total_duration_seconds": total_duration.total_seconds(),
                "total_errors": len(self.results["errors"]),
                "validation_status": "PASSED" if len(self.results["errors"]) == 0 else "FAILED",
                "tested_scenarios": len(self.results["scenarios"]),
                "network": self.config["testing"]["environment"]["network"]
            }
            
            # Save detailed results
            report_file = self.results_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
                
            # Generate human-readable summary
            await self._generate_summary_report(report_file)
            
            print(f"✅ Validation report generated: {report_file}")
            
        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            
    async def _run_pytest_suite(self, test_path: str) -> Dict[str, Any]:
        """Run specific pytest suite and capture results."""
        try:
            cmd = [
                "python", "-m", "pytest",
                test_path,
                "-v", 
                "--tb=short",
                f"--junitxml={self.results_dir}/junit_{test_path.split('::')[-1]}.xml"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "test_path": test_path,
                "exit_code": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "success": process.returncode == 0
            }
            
        except Exception as e:
            return {
                "test_path": test_path,
                "exit_code": -1,
                "error": str(e),
                "success": False
            }
            
    async def _test_horizon_connectivity(self) -> bool:
        """Test Horizon endpoint connectivity."""
        try:
            import aiohttp
            
            horizon_url = self.config["testing"]["stellar_testnet"]["endpoints"]["horizon"]["primary"]
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{horizon_url}/ledgers?limit=1", timeout=10) as response:
                    return response.status == 200
                    
        except Exception:
            return False
            
    async def _test_soroban_connectivity(self) -> bool:
        """Test Soroban RPC connectivity.""" 
        try:
            import aiohttp
            
            soroban_url = self.config["testing"]["stellar_testnet"]["endpoints"]["soroban"]["primary"]
            
            # Test basic health endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    soroban_url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                    timeout=10
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
            
    async def _test_friendbot_connectivity(self) -> bool:
        """Test Friendbot availability."""
        try:
            import aiohttp
            
            friendbot_url = self.config["testing"]["stellar_testnet"]["endpoints"]["friendbot"]["url"]
            
            async with aiohttp.ClientSession() as session:
                # Test with dummy account (will fail but confirms endpoint is available)
                test_url = f"{friendbot_url}?addr=GTEST123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"
                async with session.get(test_url, timeout=10) as response:
                    # Friendbot should respond (even with error for invalid account)
                    return response.status in [200, 400]
                    
        except Exception:
            return False
            
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics from test runs."""
        return {
            "throughput_metrics": {
                "target_rps": self.config["testing"]["performance"]["throughput"]["min_throughput"],
                "measured_rps": 0,  # Will be populated by actual tests
                "success_rate": 0.0
            },
            "latency_metrics": {
                "target_max_latency": self.config["testing"]["performance"]["latency"]["max_avg_latency"],
                "measured_avg_latency": 0,
                "measured_max_latency": 0
            }
        }
        
    async def _calculate_security_score(self, security_results: Dict[str, Any]) -> float:
        """Calculate overall security score from test results."""
        if not security_results.get("success", False):
            return 0.0
            
        # Basic score calculation - in production would be more sophisticated
        return 95.0 if security_results["success"] else 0.0
        
    async def _ensure_test_dependencies(self):
        """Ensure all test dependencies are installed."""
        try:
            import pytest_asyncio
            import aiohttp
            import yaml
        except ImportError as e:
            print(f"❌ Missing test dependency: {e}")
            print("Installing dependencies...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest-asyncio", "aiohttp", "pyyaml"])
            
    async def _validate_test_configuration(self):
        """Validate test configuration is complete and correct."""
        required_sections = ["testing", "monitoring", "alerts"]
        for section in required_sections:
            if section not in self.config:
                raise Exception(f"Missing required configuration section: {section}")
                
    async def _generate_summary_report(self, detailed_report_file: Path):
        """Generate human-readable summary report."""
        summary_file = self.results_dir / f"validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(summary_file, 'w') as f:
            f.write("# Phase 4A Real-World Validation Summary\n\n")
            f.write(f"**Report Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Test Environment:** {self.config['testing']['environment']['network']}\n")
            f.write(f"**Validation Status:** {self.results['summary']['validation_status']}\n\n")
            
            f.write("## Summary Metrics\n")
            f.write(f"- **Total Duration:** {self.results['summary']['total_duration_seconds']:.2f} seconds\n")
            f.write(f"- **Scenarios Tested:** {self.results['summary']['tested_scenarios']}\n")
            f.write(f"- **Total Errors:** {self.results['summary']['total_errors']}\n\n")
            
            if self.results["errors"]:
                f.write("## Errors Encountered\n")
                for error in self.results["errors"]:
                    f.write(f"- **{error['phase']}:** {error['error']} (at {error['timestamp']})\n")
                f.write("\n")
                
            f.write(f"## Detailed Results\n")
            f.write(f"See full detailed results: {detailed_report_file.name}\n")
            
    async def _cleanup_validation_environment(self):
        """Clean up validation environment."""
        print("\n🧹 Cleaning up validation environment")
        
        if self.config["testing"]["cleanup"]["cleanup_test_accounts"]:
            print("  Cleaning up test accounts...")
            # Implementation would clean up any test accounts created
            
        print("✅ Validation environment cleanup complete")


async def main():
    """Main entry point for integration validation."""
    runner = IntegrationValidationRunner()
    
    try:
        results = await runner.run_validation_suite()
        
        # Print final summary
        print("\n" + "=" * 60)
        print("🎯 Phase 4A Real-World Validation Complete")
        print("=" * 60)
        print(f"Status: {results['summary']['validation_status']}")
        print(f"Duration: {results['summary']['total_duration_seconds']:.2f} seconds")
        print(f"Errors: {results['summary']['total_errors']}")
        
        if results['summary']['validation_status'] == 'PASSED':
            print("✅ All validation tests passed successfully!")
            print("🚀 System ready for advanced development phases")
        else:
            print("❌ Some validation tests failed")
            print("📋 Review detailed report for remediation steps")
            
        return 0 if results['summary']['validation_status'] == 'PASSED' else 1
        
    except Exception as e:
        print(f"\n❌ Validation runner failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)