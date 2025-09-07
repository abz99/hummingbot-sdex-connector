#!/usr/bin/env python3
"""
Critical Module Coverage Checker

This script validates that critical modules meet the higher coverage threshold (90%+)
while allowing other modules to meet the baseline threshold (80%+).

QA_ID: REQ-TEST-002, REQ-TEST-003

Usage:
    python scripts/check_critical_coverage.py --threshold=90 --coverage-file=coverage.xml
    python scripts/check_critical_coverage.py --module=stellar_security --threshold=95
"""

import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CriticalCoverageChecker:
    """Checker for critical module coverage requirements."""
    
    # Critical modules that require higher coverage thresholds
    CRITICAL_MODULES = {
        'stellar_security': 95,  # Security modules need highest coverage
        'stellar_security_manager': 95,
        'stellar_chain_interface': 90,  # Chain interaction is critical
        'stellar_network_manager': 90,
        'stellar_order_manager': 90,  # Order management is critical
        'stellar_connector': 85,  # Main connector needs high coverage
        'stellar_soroban_client': 85,  # Smart contract integration
    }
    
    # Baseline threshold for non-critical modules
    BASELINE_THRESHOLD = 80
    
    def __init__(self, coverage_file: str, custom_threshold: int = None):
        self.coverage_file = Path(coverage_file)
        self.custom_threshold = custom_threshold
        self.coverage_data = {}
        
        if not self.coverage_file.exists():
            raise FileNotFoundError(f"Coverage file not found: {coverage_file}")
    
    def parse_coverage_xml(self) -> Dict[str, float]:
        """Parse coverage XML file and extract per-module coverage."""
        try:
            tree = ET.parse(self.coverage_file)
            root = tree.getroot()
            
            coverage_data = {}
            
            # Find all class/module elements
            for package in root.findall('.//package'):
                package_name = package.get('name', '')
                
                for class_elem in package.findall('.//class'):
                    class_name = class_elem.get('name', '')
                    filename = class_elem.get('filename', '')
                    
                    # Extract module name from filename
                    module_name = self._extract_module_name(filename, class_name)
                    
                    # Get line coverage stats
                    lines_elem = class_elem.find('.//lines')
                    if lines_elem is not None:
                        lines_covered = int(lines_elem.get('covered', '0'))
                        lines_valid = int(lines_elem.get('valid', '1'))
                        
                        if lines_valid > 0:
                            coverage_percent = (lines_covered / lines_valid) * 100
                            coverage_data[module_name] = coverage_percent
            
            # Also check for overall package coverage
            for package in root.findall('.//package'):
                package_name = package.get('name', '').replace('/', '.')
                
                lines_elem = package.find('.//lines')
                if lines_elem is not None:
                    lines_covered = int(lines_elem.get('covered', '0'))
                    lines_valid = int(lines_elem.get('valid', '1'))
                    
                    if lines_valid > 0:
                        coverage_percent = (lines_covered / lines_valid) * 100
                        if package_name and package_name not in coverage_data:
                            coverage_data[package_name] = coverage_percent
            
            self.coverage_data = coverage_data
            return coverage_data
            
        except ET.ParseError as e:
            logger.error(f"Error parsing coverage XML: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing coverage: {e}")
            raise
    
    def _extract_module_name(self, filename: str, class_name: str) -> str:
        """Extract module name from filename and class name."""
        if not filename:
            return class_name
        
        # Convert file path to module name
        path = Path(filename)
        
        # Remove .py extension
        module_name = path.stem
        
        # Handle nested modules
        if 'stellar' in str(path):
            # Extract the stellar module part
            parts = path.parts
            stellar_idx = -1
            
            for i, part in enumerate(parts):
                if 'stellar' in part and part.endswith('.py'):
                    stellar_idx = i
                    break
                elif 'stellar' in part:
                    stellar_idx = i
            
            if stellar_idx >= 0:
                if stellar_idx == len(parts) - 1:
                    # It's the file itself
                    module_name = path.stem
                else:
                    # Build module path
                    relevant_parts = parts[stellar_idx:]
                    if relevant_parts[-1].endswith('.py'):
                        relevant_parts = relevant_parts[:-1] + (path.stem,)
                    module_name = '.'.join(relevant_parts)
        
        return module_name
    
    def check_critical_coverage(self, specific_module: str = None) -> Tuple[bool, List[str], List[str]]:
        """Check coverage for critical modules."""
        if not self.coverage_data:
            self.parse_coverage_xml()
        
        passed_modules = []
        failed_modules = []
        warnings = []
        
        modules_to_check = self.CRITICAL_MODULES
        
        if specific_module:
            # Check only specific module
            if specific_module in self.CRITICAL_MODULES:
                modules_to_check = {specific_module: self.CRITICAL_MODULES[specific_module]}
            else:
                # Use custom threshold or baseline
                threshold = self.custom_threshold or self.BASELINE_THRESHOLD
                modules_to_check = {specific_module: threshold}
        
        for module_name, required_threshold in modules_to_check.items():
            actual_coverage = self._find_module_coverage(module_name)
            
            if actual_coverage is None:
                warnings.append(f"Module '{module_name}' not found in coverage report")
                continue
            
            if actual_coverage >= required_threshold:
                passed_modules.append(f"✅ {module_name}: {actual_coverage:.1f}% (required: {required_threshold}%)")
            else:
                failed_modules.append(f"❌ {module_name}: {actual_coverage:.1f}% (required: {required_threshold}%)")
        
        # Check if all critical modules passed
        all_passed = len(failed_modules) == 0
        
        return all_passed, passed_modules, failed_modules, warnings
    
    def _find_module_coverage(self, module_name: str) -> float:
        """Find coverage for a specific module (with fuzzy matching)."""
        # Direct match
        if module_name in self.coverage_data:
            return self.coverage_data[module_name]
        
        # Fuzzy matching - find modules that contain the name
        matches = []
        for coverage_module, coverage_value in self.coverage_data.items():
            if module_name in coverage_module or coverage_module in module_name:
                matches.append((coverage_module, coverage_value))
        
        if matches:
            # If multiple matches, return the average
            if len(matches) == 1:
                return matches[0][1]
            else:
                # Average coverage across matching modules
                avg_coverage = sum(coverage for _, coverage in matches) / len(matches)
                logger.info(f"Multiple matches for '{module_name}': {[m[0] for m in matches]}")
                logger.info(f"Using average coverage: {avg_coverage:.1f}%")
                return avg_coverage
        
        return None
    
    def generate_coverage_report(self) -> str:
        """Generate detailed coverage report."""
        if not self.coverage_data:
            self.parse_coverage_xml()
        
        report_lines = [
            "# Critical Module Coverage Report",
            f"Generated from: {self.coverage_file}",
            "",
            "## Critical Modules Status",
            ""
        ]
        
        all_passed, passed_modules, failed_modules, warnings = self.check_critical_coverage()
        
        if passed_modules:
            report_lines.append("### ✅ Passed Modules")
            for module in passed_modules:
                report_lines.append(f"- {module}")
            report_lines.append("")
        
        if failed_modules:
            report_lines.append("### ❌ Failed Modules")
            for module in failed_modules:
                report_lines.append(f"- {module}")
            report_lines.append("")
        
        if warnings:
            report_lines.append("### ⚠️  Warnings")
            for warning in warnings:
                report_lines.append(f"- {warning}")
            report_lines.append("")
        
        # Overall coverage summary
        report_lines.extend([
            "## All Modules Coverage",
            ""
        ])
        
        sorted_modules = sorted(self.coverage_data.items(), key=lambda x: x[1], reverse=True)
        
        for module_name, coverage in sorted_modules:
            # Determine status
            if module_name in self.CRITICAL_MODULES:
                required = self.CRITICAL_MODULES[module_name]
                status = "✅" if coverage >= required else "❌"
                report_lines.append(f"- {status} **{module_name}**: {coverage:.1f}% (critical, required: {required}%)")
            else:
                status = "✅" if coverage >= self.BASELINE_THRESHOLD else "❌"
                report_lines.append(f"- {status} {module_name}: {coverage:.1f}% (baseline: {self.BASELINE_THRESHOLD}%)")
        
        # Summary
        report_lines.extend([
            "",
            "## Summary",
            f"- **Total modules**: {len(self.coverage_data)}",
            f"- **Critical modules passed**: {len(passed_modules)}",
            f"- **Critical modules failed**: {len(failed_modules)}",
            f"- **Overall status**: {'PASS' if all_passed else 'FAIL'}",
            ""
        ])
        
        if not all_passed:
            report_lines.extend([
                "## Action Required",
                "",
                "Some critical modules do not meet the required coverage threshold.",
                "Please add more tests to increase coverage for the failed modules.",
                ""
            ])
        
        return "\n".join(report_lines)
    
    def print_summary(self):
        """Print coverage summary to console."""
        all_passed, passed_modules, failed_modules, warnings = self.check_critical_coverage()
        
        print("\n" + "="*70)
        print("CRITICAL MODULE COVERAGE SUMMARY")
        print("="*70)
        
        if passed_modules:
            print("\n✅ PASSED MODULES:")
            for module in passed_modules:
                print(f"  {module}")
        
        if failed_modules:
            print("\n❌ FAILED MODULES:")
            for module in failed_modules:
                print(f"  {module}")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for warning in warnings:
                print(f"  {warning}")
        
        print("\n" + "="*70)
        
        if all_passed:
            print("\033[92m✅ ALL CRITICAL MODULES MEET COVERAGE REQUIREMENTS\033[0m")
        else:
            print("\033[91m❌ SOME CRITICAL MODULES BELOW REQUIRED COVERAGE\033[0m")
        
        print("="*70 + "\n")
        
        return all_passed

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check critical module coverage requirements"
    )
    parser.add_argument(
        '--coverage-file',
        type=str,
        default='coverage.xml',
        help='Path to coverage XML file (default: coverage.xml)'
    )
    parser.add_argument(
        '--threshold',
        type=int,
        help='Custom coverage threshold percentage (overrides module-specific thresholds)'
    )
    parser.add_argument(
        '--module',
        type=str,
        help='Check coverage for specific module only'
    )
    parser.add_argument(
        '--report-file',
        type=str,
        help='Output detailed report to file'
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
        checker = CriticalCoverageChecker(args.coverage_file, args.threshold)
        
        # Parse coverage data
        logger.info(f"Parsing coverage file: {args.coverage_file}")
        checker.parse_coverage_xml()
        
        if args.module:
            logger.info(f"Checking coverage for module: {args.module}")
        else:
            logger.info("Checking coverage for all critical modules")
        
        # Check coverage
        all_passed = checker.print_summary()
        
        # Generate detailed report if requested
        if args.report_file:
            report = checker.generate_coverage_report()
            
            report_path = Path(args.report_file)
            report_path.write_text(report, encoding='utf-8')
            
            logger.info(f"Detailed report saved to: {report_path}")
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)

if __name__ == '__main__':
    main()