#!/usr/bin/env python3
"""
PR Review Script for SpecKit Compliance
Checks PRs for SpecKit-driven development, test coverage, code quality, and documentation.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class ReviewResult:
    """Result of a review check"""
    passed: bool
    findings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)


class PRReviewer:
    """Automated PR reviewer for SpecKit compliance"""
    
    def __init__(self, repo_root: Path, timeout: int = 120):
        self.repo_root = repo_root
        self.specs_dir = repo_root / "specs"
        self.app_dir = repo_root / "app"
        self.timeout = timeout
        
    def run_command(self, cmd: List[str], cwd: Path = None) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", f"Command timed out after {self.timeout} seconds"
        except Exception as e:
            return 1, "", str(e)
    
    def check_speckit_artifacts(self) -> ReviewResult:
        """Check for SpecKit-driven development artifacts"""
        result = ReviewResult(passed=True)
        
        # Check for spec.md
        spec_files = list(self.specs_dir.rglob("spec.md"))
        if spec_files:
            result.findings.append(f"✅ Found {len(spec_files)} spec.md file(s)")
            for spec in spec_files:
                # Validate spec.md content
                content = spec.read_text()
                if "# Feature Specification:" in content or "## Overview" in content:
                    result.info.append(f"  - {spec.relative_to(self.repo_root)}: Valid structure")
                else:
                    result.warnings.append(f"  - {spec.relative_to(self.repo_root)}: May be incomplete")
        else:
            result.errors.append("❌ No spec.md found in specs/ directory")
            result.passed = False
        
        # Check for plan.md
        plan_files = list(self.specs_dir.rglob("plan.md"))
        if plan_files:
            result.findings.append(f"✅ Found {len(plan_files)} plan.md file(s)")
            for plan in plan_files:
                content = plan.read_text()
                if "# Implementation Plan:" in content or "## Summary" in content:
                    result.info.append(f"  - {plan.relative_to(self.repo_root)}: Valid structure")
                else:
                    result.warnings.append(f"  - {plan.relative_to(self.repo_root)}: May be incomplete")
        else:
            result.warnings.append("⚠️ No plan.md found - Implementation plan is recommended")
        
        # Check for tasks.md
        tasks_files = list(self.specs_dir.rglob("tasks.md"))
        if tasks_files:
            result.findings.append(f"✅ Found {len(tasks_files)} tasks.md file(s)")
            for tasks in tasks_files:
                content = tasks.read_text()
                # Count tasks
                task_count = content.count("- [x]") + content.count("- [ ]")
                completed = content.count("- [x]")
                result.info.append(
                    f"  - {tasks.relative_to(self.repo_root)}: "
                    f"{completed}/{task_count} tasks completed"
                )
        else:
            result.warnings.append("⚠️ No tasks.md found - Task breakdown is recommended")
        
        return result
    
    def check_test_coverage(self) -> ReviewResult:
        """Check for test files and run tests"""
        result = ReviewResult(passed=True)
        
        tests_dir = self.app_dir / "tests"
        if not tests_dir.exists():
            result.info.append("ℹ️ No tests directory found - Tests may not be applicable")
            return result
        
        # Find test files
        test_files = list(tests_dir.glob("test_*.py"))
        if not test_files:
            result.warnings.append("⚠️ No test files found in app/tests/")
            return result
        
        result.findings.append(f"✅ Found {len(test_files)} test file(s)")
        for test_file in test_files:
            result.info.append(f"  - {test_file.relative_to(self.repo_root)}")
        
        # Try to run tests
        if (self.app_dir / "pyproject.toml").exists():
            returncode, stdout, stderr = self.run_command(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=self.app_dir
            )
            
            if returncode == 0:
                result.findings.append("✅ All tests passed")
                # Extract test summary
                for line in stdout.split("\n"):
                    if "passed" in line.lower():
                        result.info.append(f"  {line.strip()}")
            else:
                result.warnings.append("⚠️ Some tests failed or could not run")
                result.info.append(f"  Check test output for details")
        
        return result
    
    def check_code_quality(self) -> ReviewResult:
        """Check code quality with ruff and mypy"""
        result = ReviewResult(passed=True)
        
        src_dir = self.app_dir / "src"
        if not src_dir.exists():
            result.info.append("ℹ️ No app/src directory found")
            return result
        
        # Run ruff linting
        returncode, stdout, stderr = self.run_command(
            ["ruff", "check", str(src_dir), "--output-format=concise"]
        )
        
        if returncode == 0:
            result.findings.append("✅ Ruff linting passed - No style violations")
        else:
            result.errors.append("❌ Ruff linting found issues")
            result.passed = False
            # Include first few errors
            errors = stdout.split("\n")[:10]
            for error in errors:
                if error.strip():
                    result.info.append(f"  {error.strip()}")
        
        # Run mypy type checking
        returncode, stdout, stderr = self.run_command(
            ["mypy", str(src_dir), "--no-error-summary"]
        )
        
        if returncode == 0:
            result.findings.append("✅ Type checking passed - No type errors")
        else:
            result.warnings.append("⚠️ Mypy found type issues")
            # Include first few type errors
            errors = (stdout + stderr).split("\n")[:10]
            for error in errors:
                if error.strip() and "error:" in error.lower():
                    result.info.append(f"  {error.strip()}")
        
        return result
    
    def check_documentation(self) -> ReviewResult:
        """Check for documentation"""
        result = ReviewResult(passed=True)
        
        # Check for README.md
        readme = self.app_dir / "README.md"
        if readme.exists():
            lines = len(readme.read_text().split("\n"))
            if lines > 50:
                result.findings.append(f"✅ README.md present with {lines} lines")
            else:
                result.warnings.append(f"⚠️ README.md exists but may need more content ({lines} lines)")
        else:
            result.warnings.append("⚠️ No README.md found in app/ directory")
        
        # Check for inline documentation
        src_dir = self.app_dir / "src"
        if src_dir.exists():
            docstring_count = 0
            py_files = list(src_dir.rglob("*.py"))
            
            for py_file in py_files:
                try:
                    content = py_file.read_text()
                    docstring_count += content.count('"""')
                except Exception:
                    pass
            
            if docstring_count > 10:
                result.findings.append(f"✅ Good inline documentation - {docstring_count} docstrings found")
            else:
                result.info.append(f"ℹ️ Limited inline documentation - {docstring_count} docstrings found")
        
        return result
    
    def check_constitution_compliance(self) -> ReviewResult:
        """Check compliance with project constitution"""
        result = ReviewResult(passed=True)
        
        # Check for app/ directory structure
        if not self.app_dir.exists():
            result.errors.append("❌ No app/ directory - Code should be in app/")
            result.passed = False
            return result
        
        result.findings.append("✅ Application code in app/ directory")
        
        # Check pyproject.toml requirements
        pyproject = self.app_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            
            # Python version check
            if "requires-python" in content and "3.12" in content:
                result.findings.append("✅ Python >=3.12 requirement specified")
            else:
                result.warnings.append("⚠️ Python version requirement unclear")
            
            # Check for required dependencies
            if "pydantic" in content:
                result.findings.append("✅ Pydantic used for type safety")
            
            if "agent-framework" in content or "microsoft-agent-framework" in content:
                result.findings.append("✅ microsoft-agent-framework dependency present")
            
            if "ruff" in content:
                result.info.append("  - Ruff configured for linting")
            
            if "mypy" in content:
                result.info.append("  - mypy configured for type checking")
        
        # Check for logging utilities
        logging_utils = self.app_dir / "src" / "logging_utils.py"
        if logging_utils.exists():
            result.findings.append("✅ Structured logging utilities present")
        
        return result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate complete review report"""
        print("🤖 Running PR Review - SpecKit Compliance Check...\n")
        
        # Run all checks
        speckit_result = self.check_speckit_artifacts()
        test_result = self.check_test_coverage()
        quality_result = self.check_code_quality()
        docs_result = self.check_documentation()
        constitution_result = self.check_constitution_compliance()
        
        # Determine overall status
        all_passed = all([
            speckit_result.passed,
            quality_result.passed,
            constitution_result.passed
        ])
        
        # Generate report
        report = {
            "overall_passed": all_passed,
            "speckit": self._format_result(speckit_result),
            "tests": self._format_result(test_result),
            "quality": self._format_result(quality_result),
            "documentation": self._format_result(docs_result),
            "constitution": self._format_result(constitution_result)
        }
        
        # Print report
        self._print_report(report, all_passed)
        
        return report
    
    def _format_result(self, result: ReviewResult) -> Dict[str, Any]:
        """Format a review result for reporting"""
        return {
            "passed": result.passed,
            "findings": result.findings,
            "errors": result.errors,
            "warnings": result.warnings,
            "info": result.info
        }
    
    def _print_report(self, report: Dict[str, Any], all_passed: bool):
        """Print formatted report to console"""
        print("=" * 80)
        print(f"Overall Status: {'✅ PASSED' if all_passed else '⚠️ NEEDS ATTENTION'}")
        print("=" * 80)
        
        sections = [
            ("📋 SpecKit-Driven Development", report["speckit"]),
            ("🧪 Test Coverage", report["tests"]),
            ("🔍 Code Quality", report["quality"]),
            ("📚 Documentation", report["documentation"]),
            ("📜 Constitution Compliance", report["constitution"])
        ]
        
        for title, section in sections:
            print(f"\n{title}")
            print("-" * 80)
            
            for finding in section["findings"]:
                print(finding)
            for error in section["errors"]:
                print(error)
            for warning in section["warnings"]:
                print(warning)
            for info in section["info"]:
                print(info)
        
        print("\n" + "=" * 80)
        print("Review complete. Please address any errors (❌) or warnings (⚠️).")
        print("=" * 80)


def main():
    """Main entry point"""
    # Get repository root
    repo_root = Path(__file__).parent.parent.parent
    
    # Create reviewer
    reviewer = PRReviewer(repo_root)
    
    # Generate report
    report = reviewer.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if report["overall_passed"] else 1)


if __name__ == "__main__":
    main()
