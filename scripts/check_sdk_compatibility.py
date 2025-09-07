#!/usr/bin/env python3
"""
Stellar SDK Compatibility Checker

This script validates compatibility between the Stellar Hummingbot connector 
and different versions of the Python Stellar SDK (py-stellar-base/stellar-sdk).

QA_ID: REQ-COMPAT-001, REQ-COMPAT-002

Usage:
    python scripts/check_sdk_compatibility.py --sdk-version=8.1.0
    python scripts/check_sdk_compatibility.py --all-versions
    python scripts/check_sdk_compatibility.py --matrix-test
"""

import sys
import argparse
import importlib
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from packaging import version
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CompatibilityResult:
    """Compatibility test result."""
    sdk_version: str
    python_version: str
    success: bool
    errors: List[str]
    warnings: List[str]
    test_results: Dict[str, Any]
    execution_time: float

class StellarSDKCompatibilityChecker:
    """Main compatibility checker class."""
    
    # Supported SDK version matrix
    SUPPORTED_MATRIX = {
        '3.9': ['7.17.0', '8.0.0', '8.1.0'],
        '3.10': ['7.17.0', '8.0.0', '8.1.0', '8.2.0', '8.2.1'],
        '3.11': ['7.17.0', '8.0.0', '8.1.0', '8.2.0', '8.2.1'],
        '3.12': ['8.0.0', '8.1.0', '8.2.0', '8.2.1']
    }
    
    # Known breaking changes between versions
    BREAKING_CHANGES = {
        '8.0.0': [
            'Removed deprecated methods from AccountCallBuilder',
            'Changed default timeout from 30s to 60s',
            'Updated transaction envelope format'
        ],
        '8.1.0': [
            'Added new Soroban contract invocation methods',
            'Changed fee calculation for smart contracts'
        ],
        '8.2.0': [
            'Updated asset serialization format',
            'Changed path payment finding algorithm'
        ]
    }
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.current_python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.test_results: List[CompatibilityResult] = []
    
    def get_current_sdk_version(self) -> Optional[str]:
        """Get currently installed Stellar SDK version."""
        try:
            import stellar_sdk
            return stellar_sdk.__version__
        except ImportError:
            logger.error("Stellar SDK not installed")
            return None
        except AttributeError:
            # Fallback for older versions
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', 'stellar-sdk'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Version:'):
                            return line.split(':')[1].strip()
            except subprocess.TimeoutExpired:
                logger.error("Timeout getting SDK version")
            return None
    
    def check_version_compatibility(self, sdk_version: str) -> CompatibilityResult:
        """Check compatibility with specific SDK version."""
        start_time = time.time()
        
        result = CompatibilityResult(
            sdk_version=sdk_version,
            python_version=self.current_python_version,
            success=True,
            errors=[],
            warnings=[],
            test_results={},
            execution_time=0.0
        )
        
        logger.info(f"Checking SDK version {sdk_version} compatibility...")
        
        try:
            # 1. Check if version is in supported matrix
            if not self._is_version_supported(sdk_version):
                result.success = False
                result.errors.append(
                    f"SDK version {sdk_version} not supported with Python {self.current_python_version}"
                )
                return result
            
            # 2. Test core imports
            import_results = self._test_core_imports()
            result.test_results['imports'] = import_results
            
            if not import_results['success']:
                result.success = False
                result.errors.extend(import_results['errors'])
            
            # 3. Test basic functionality
            basic_tests = self._test_basic_functionality()
            result.test_results['basic_functionality'] = basic_tests
            
            if not basic_tests['success']:
                result.success = False
                result.errors.extend(basic_tests['errors'])
            
            # 4. Test connector-specific functionality
            connector_tests = self._test_connector_compatibility()
            result.test_results['connector'] = connector_tests
            
            if not connector_tests['success']:
                result.success = False
                result.errors.extend(connector_tests['errors'])
            
            # 5. Check for breaking changes
            breaking_changes = self._check_breaking_changes(sdk_version)
            result.test_results['breaking_changes'] = breaking_changes
            
            if breaking_changes['has_breaking_changes']:
                result.warnings.extend(breaking_changes['changes'])
            
            # 6. Test Soroban compatibility (SDK 8.0+)
            if version.parse(sdk_version) >= version.parse('8.0.0'):
                soroban_tests = self._test_soroban_compatibility()
                result.test_results['soroban'] = soroban_tests
                
                if not soroban_tests['success']:
                    result.warnings.extend(soroban_tests['warnings'])
        
        except Exception as e:
            result.success = False
            result.errors.append(f"Unexpected error during compatibility check: {str(e)}")
            logger.exception("Error during compatibility check")
        
        finally:
            result.execution_time = time.time() - start_time
        
        return result
    
    def _is_version_supported(self, sdk_version: str) -> bool:
        """Check if SDK version is supported with current Python version."""
        supported_versions = self.SUPPORTED_MATRIX.get(self.current_python_version, [])
        return sdk_version in supported_versions
    
    def _test_core_imports(self) -> Dict[str, Any]:
        """Test core Stellar SDK imports."""
        result = {'success': True, 'errors': [], 'imports_tested': []}
        
        core_imports = [
            'stellar_sdk',
            'stellar_sdk.keypair',
            'stellar_sdk.account',
            'stellar_sdk.network',
            'stellar_sdk.transaction_builder',
            'stellar_sdk.server',
            'stellar_sdk.asset',
            'stellar_sdk.operation',
            'stellar_sdk.exceptions'
        ]
        
        for import_name in core_imports:
            try:
                importlib.import_module(import_name)
                result['imports_tested'].append(f"✅ {import_name}")
                logger.debug(f"Successfully imported {import_name}")
            except ImportError as e:
                result['success'] = False
                result['errors'].append(f"Failed to import {import_name}: {str(e)}")
                result['imports_tested'].append(f"❌ {import_name}")
        
        return result
    
    def _test_basic_functionality(self) -> Dict[str, Any]:
        """Test basic SDK functionality."""
        result = {'success': True, 'errors': [], 'tests_run': []}
        
        try:
            # Test 1: Keypair generation
            from stellar_sdk import Keypair
            keypair = Keypair.random()
            assert keypair.secret is not None
            assert keypair.public_key is not None
            result['tests_run'].append("✅ Keypair generation")
            
            # Test 2: Account creation
            from stellar_sdk import Account
            account = Account(keypair.public_key, sequence=1)
            # Handle API change between SDK versions
            account_id = getattr(account, 'account_id', None) or str(account.account)
            assert account_id == keypair.public_key or keypair.public_key in str(account_id)
            assert account.sequence == 1
            result['tests_run'].append("✅ Account creation")
            
            # Test 3: Asset creation
            from stellar_sdk import Asset
            native_asset = Asset.native()
            # Handle API change - new constructor pattern
            custom_asset = Asset("USD", keypair.public_key)
            assert native_asset.is_native()
            assert not custom_asset.is_native()
            result['tests_run'].append("✅ Asset creation")
            
            # Test 4: Transaction builder (basic)
            from stellar_sdk import TransactionBuilder, Network
            from stellar_sdk.operation import Payment
            
            builder = TransactionBuilder(
                source_account=account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100
            )
            
            payment_op = Payment(
                destination=Keypair.random().public_key,
                asset=Asset.native(),
                amount="1.0"
            )
            
            transaction = builder.append_operation(payment_op).set_timeout(30).build()
            assert transaction is not None
            result['tests_run'].append("✅ Transaction building")
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Basic functionality test failed: {str(e)}")
            result['tests_run'].append(f"❌ Basic functionality: {str(e)}")
        
        return result
    
    def _test_connector_compatibility(self) -> Dict[str, Any]:
        """Test connector-specific compatibility."""
        result = {'success': True, 'errors': [], 'warnings': [], 'tests_run': []}
        
        try:
            # Import Keypair at module level to avoid undefined reference
            from stellar_sdk import Keypair
            
            # Test 1: Server initialization patterns used by connector
            from stellar_sdk import Server
            
            # Test different server initialization patterns
            server_testnet = Server("https://horizon-testnet.stellar.org")
            assert server_testnet is not None
            result['tests_run'].append("✅ Server initialization")
            
            # Test 2: Fee stats (used for dynamic fee calculation)
            try:
                from stellar_sdk.call_builder.fee_stats_call_builder import FeeStatsCallBuilder
                result['tests_run'].append("✅ Fee stats builder available")
            except ImportError:
                result['warnings'].append("FeeStatsCallBuilder not available - may affect fee calculation")
                result['tests_run'].append("⚠️  Fee stats builder not available")
            
            # Test 3: Path payment operations (core to connector)
            from stellar_sdk.operation import PathPaymentStrictReceive, PathPaymentStrictSend
            from stellar_sdk import Asset
            
            path_payment_receive = PathPaymentStrictReceive(
                destination=Keypair.random().public_key,
                send_asset=Asset.native(),
                send_max="10.0",
                dest_asset=Asset("USD", Keypair.random().public_key),
                dest_amount="5.0",
                path=[]
            )
            assert path_payment_receive is not None
            result['tests_run'].append("✅ Path payment operations")
            
            # Test 4: Claimable balance operations (may be used for advanced features)
            try:
                from stellar_sdk.operation import CreateClaimableBalance, ClaimClaimableBalance
                result['tests_run'].append("✅ Claimable balance operations available")
            except ImportError:
                result['warnings'].append("Claimable balance operations not available")
                result['tests_run'].append("⚠️  Claimable balance operations not available")
            
            # Test 5: Liquidity pool operations (for AMM integration)
            try:
                from stellar_sdk.operation import ChangeTrust
                from stellar_sdk.liquidity_pool_asset import LiquidityPoolAsset
                from stellar_sdk.asset import Asset
                
                # Try to create liquidity pool asset
                lp_asset = LiquidityPoolAsset(
                    asset_a=Asset.native(),
                    asset_b=Asset("USD", Keypair.random().public_key),
                    fee=30  # 0.3%
                )
                assert lp_asset is not None
                result['tests_run'].append("✅ Liquidity pool operations available")
            except (ImportError, AttributeError):
                result['warnings'].append("Liquidity pool operations not available - AMM features may be limited")
                result['tests_run'].append("⚠️  Liquidity pool operations not available")
        
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Connector compatibility test failed: {str(e)}")
            result['tests_run'].append(f"❌ Connector compatibility: {str(e)}")
        
        return result
    
    def _test_soroban_compatibility(self) -> Dict[str, Any]:
        """Test Soroban smart contract compatibility (SDK 8.0+)."""
        result = {'success': True, 'errors': [], 'warnings': [], 'tests_run': []}
        
        try:
            # Test 1: Soroban server import
            try:
                from stellar_sdk.soroban_server import SorobanServer
                soroban_server = SorobanServer("https://soroban-testnet.stellar.org")
                assert soroban_server is not None
                result['tests_run'].append("✅ SorobanServer available")
            except ImportError:
                result['warnings'].append("SorobanServer not available - Soroban features will be limited")
                result['tests_run'].append("⚠️  SorobanServer not available")
                return result
            
            # Test 2: Contract operations
            try:
                from stellar_sdk.operation import InvokeHostFunction, CreateContract
                result['tests_run'].append("✅ Contract operations available")
            except ImportError:
                result['warnings'].append("Contract operations not available")
                result['tests_run'].append("⚠️  Contract operations not available")
            
            # Test 3: Soroban data structures
            try:
                from stellar_sdk.xdr import SCVal, SCSymbol
                result['tests_run'].append("✅ Soroban data structures available")
            except ImportError:
                result['warnings'].append("Soroban data structures not available")
                result['tests_run'].append("⚠️  Soroban data structures not available")
            
            # Test 4: Contract invocation helpers
            try:
                from stellar_sdk.contract import Contract
                # Note: This may not exist in all versions
                result['tests_run'].append("✅ Contract helpers available")
            except ImportError:
                result['warnings'].append("Contract helpers not available - manual XDR construction required")
                result['tests_run'].append("⚠️  Contract helpers not available")
        
        except Exception as e:
            result['warnings'].append(f"Soroban compatibility test error: {str(e)}")
            result['tests_run'].append(f"⚠️  Soroban test error: {str(e)}")
        
        return result
    
    def _check_breaking_changes(self, sdk_version: str) -> Dict[str, Any]:
        """Check for known breaking changes in SDK version."""
        result = {
            'has_breaking_changes': False,
            'changes': [],
            'migration_required': False
        }
        
        if sdk_version in self.BREAKING_CHANGES:
            result['has_breaking_changes'] = True
            result['changes'] = self.BREAKING_CHANGES[sdk_version]
            result['migration_required'] = True
        
        return result
    
    def run_matrix_test(self) -> List[CompatibilityResult]:
        """Run compatibility tests across supported version matrix."""
        python_ver = self.current_python_version
        supported_versions = self.SUPPORTED_MATRIX.get(python_ver, [])
        
        logger.info(f"Running matrix test for Python {python_ver}")
        logger.info(f"Testing SDK versions: {supported_versions}")
        
        results = []
        current_sdk = self.get_current_sdk_version()
        
        for sdk_version in supported_versions:
            if current_sdk != sdk_version:
                logger.warning(f"Current SDK version ({current_sdk}) != test version ({sdk_version})")
                logger.warning("Install target SDK version for accurate testing")
                continue
            
            result = self.check_version_compatibility(sdk_version)
            results.append(result)
        
        self.test_results = results
        return results
    
    def generate_compatibility_report(self, results: List[CompatibilityResult]) -> str:
        """Generate detailed compatibility report."""
        report_lines = [
            "# Stellar SDK Compatibility Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            f"Python Version: {self.current_python_version}",
            "",
            "## Summary",
            ""
        ]
        
        # Summary statistics
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        
        report_lines.extend([
            f"- **Total SDK versions tested**: {total_tests}",
            f"- **Successful**: {successful_tests}",
            f"- **Failed**: {failed_tests}",
            f"- **Success rate**: {(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "- **Success rate**: N/A",
            ""
        ])
        
        # Detailed results
        for result in results:
            status_emoji = "✅" if result.success else "❌"
            report_lines.extend([
                f"## {status_emoji} SDK Version {result.sdk_version}",
                f"- **Status**: {'PASS' if result.success else 'FAIL'}",
                f"- **Execution Time**: {result.execution_time:.2f}s",
                ""
            ])
            
            if result.errors:
                report_lines.extend([
                    "### Errors:",
                    ""
                ])
                for error in result.errors:
                    report_lines.append(f"- ❌ {error}")
                report_lines.append("")
            
            if result.warnings:
                report_lines.extend([
                    "### Warnings:",
                    ""
                ])
                for warning in result.warnings:
                    report_lines.append(f"- ⚠️  {warning}")
                report_lines.append("")
            
            # Test details
            if result.test_results:
                report_lines.extend([
                    "### Test Results:",
                    ""
                ])
                
                for test_category, test_result in result.test_results.items():
                    if isinstance(test_result, dict) and 'tests_run' in test_result:
                        report_lines.append(f"**{test_category.title()}:**")
                        for test_line in test_result['tests_run']:
                            report_lines.append(f"  {test_line}")
                        report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            ""
        ])
        
        if failed_tests > 0:
            report_lines.extend([
                "⚠️  **Action Required**: Some compatibility tests failed.",
                "",
                "**Recommended actions**:",
                "1. Review failed test details above",
                "2. Check for breaking changes in target SDK versions", 
                "3. Update connector code to handle compatibility issues",
                "4. Consider pinning to a known-good SDK version",
                ""
            ])
        else:
            report_lines.extend([
                "✅ **All compatibility tests passed**",
                "",
                "The connector is compatible with the tested SDK versions.",
                ""
            ])
        
        return "\n".join(report_lines)
    
    def save_report(self, results: List[CompatibilityResult], output_file: str):
        """Save compatibility report to file."""
        report = self.generate_compatibility_report(results)
        
        output_path = Path(output_file)
        output_path.write_text(report, encoding='utf-8')
        
        logger.info(f"Compatibility report saved to: {output_path}")
    
    def print_summary(self, results: List[CompatibilityResult]):
        """Print compatibility test summary to console."""
        print("\n" + "="*60)
        print("STELLAR SDK COMPATIBILITY TEST SUMMARY")
        print("="*60)
        
        for result in results:
            status = "PASS" if result.success else "FAIL"
            status_color = "\033[92m" if result.success else "\033[91m"  # Green or Red
            reset_color = "\033[0m"
            
            print(f"{status_color}SDK {result.sdk_version}: {status}{reset_color} "
                  f"({result.execution_time:.2f}s)")
            
            if result.errors:
                for error in result.errors[:2]:  # Show first 2 errors
                    print(f"  ❌ {error}")
                if len(result.errors) > 2:
                    print(f"  ... and {len(result.errors) - 2} more errors")
            
            if result.warnings:
                for warning in result.warnings[:1]:  # Show first warning
                    print(f"  ⚠️  {warning}")
                if len(result.warnings) > 1:
                    print(f"  ... and {len(result.warnings) - 1} more warnings")
        
        print("="*60)
        
        # Overall result
        successful_tests = sum(1 for r in results if r.success)
        total_tests = len(results)
        
        if successful_tests == total_tests and total_tests > 0:
            print("\033[92m✅ ALL COMPATIBILITY TESTS PASSED\033[0m")
        elif successful_tests > 0:
            print(f"\033[93m⚠️  PARTIAL SUCCESS: {successful_tests}/{total_tests} tests passed\033[0m")
        else:
            print("\033[91m❌ ALL COMPATIBILITY TESTS FAILED\033[0m")
        
        print("="*60 + "\n")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check Stellar SDK compatibility with the Hummingbot connector"
    )
    parser.add_argument(
        '--sdk-version', 
        type=str,
        help='Specific SDK version to test (e.g., 8.1.0)'
    )
    parser.add_argument(
        '--all-versions',
        action='store_true',
        help='Test all supported SDK versions for current Python version'
    )
    parser.add_argument(
        '--matrix-test',
        action='store_true',
        help='Run full compatibility matrix test'
    )
    parser.add_argument(
        '--report-file',
        type=str,
        default='compatibility_report.md',
        help='Output file for detailed report (default: compatibility_report.md)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    checker = StellarSDKCompatibilityChecker()
    
    # Determine what to test
    if args.sdk_version:
        # Test specific version
        current_version = checker.get_current_sdk_version()
        if current_version != args.sdk_version:
            logger.error(f"Current SDK version ({current_version}) != requested version ({args.sdk_version})")
            logger.error(f"Please install SDK version {args.sdk_version} first:")
            logger.error(f"  pip install stellar-sdk=={args.sdk_version}")
            sys.exit(1)
        
        result = checker.check_version_compatibility(args.sdk_version)
        results = [result]
    
    elif args.all_versions or args.matrix_test:
        # Test all supported versions
        current_version = checker.get_current_sdk_version()
        python_ver = checker.current_python_version
        supported = checker.SUPPORTED_MATRIX.get(python_ver, [])
        
        if not supported:
            logger.error(f"No supported SDK versions found for Python {python_ver}")
            sys.exit(1)
        
        if current_version not in supported:
            logger.warning(f"Current SDK version ({current_version}) not in supported list: {supported}")
            logger.warning("Results may not be accurate for unsupported versions")
        
        results = checker.run_matrix_test()
    
    else:
        # Default: test current version
        current_version = checker.get_current_sdk_version()
        if not current_version:
            logger.error("Could not determine current SDK version")
            sys.exit(1)
        
        logger.info(f"Testing current SDK version: {current_version}")
        result = checker.check_version_compatibility(current_version)
        results = [result]
    
    # Print results
    checker.print_summary(results)
    
    # Save detailed report
    if results:
        checker.save_report(results, args.report_file)
    
    # Exit with appropriate code
    all_passed = all(r.success for r in results)
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()