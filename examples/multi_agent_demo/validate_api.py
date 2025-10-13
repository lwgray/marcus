"""
API Validation Suite for Marcus Multi-Agent Demo.

This script validates that the implemented API matches the OpenAPI specification
and measures quality metrics (test coverage, type safety, spec compliance).
"""

import asyncio
import json
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Hashable, Optional

import httpx
import yaml
from openapi_core import OpenAPI


class APIValidator:
    """Validates API implementation against OpenAPI specification."""

    def __init__(self, spec_path: str, base_url: str):
        """
        Initialize the validator.

        Parameters
        ----------
        spec_path : str
            Path to the OpenAPI specification YAML file
        base_url : str
            Base URL of the API to test
        """
        self.spec_path = Path(spec_path)
        self.base_url = base_url
        self.spec = self._load_spec()
        self.openapi = OpenAPI.from_dict(self.spec)
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "endpoints_tested": 0,
            "endpoints_passed": 0,
            "endpoints_failed": 0,
            "failures": [],
        }

    def _load_spec(self) -> Mapping[Hashable, Any]:
        """Load OpenAPI specification from YAML file."""
        with open(self.spec_path, "r") as f:
            spec: Mapping[Hashable, Any] = yaml.safe_load(f)
            return spec

    async def validate_endpoint(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Validate a single endpoint against the specification.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, PUT, DELETE)
        path : str
            API path (e.g., /auth/login)
        headers : Dict[str, str], optional
            Request headers
        json_data : Dict[str, Any], optional
            JSON request body
        params : Dict[str, Any], optional
            Query parameters

        Returns
        -------
        bool
            True if endpoint passes validation, False otherwise
        """
        url = f"{self.base_url}{path}"
        self.results["endpoints_tested"] += 1

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers or {},
                    json=json_data,
                    params=params,
                    timeout=10.0,
                )

            # Validate response against spec
            # Note: This is a simplified validation - full implementation would use
            # openapi-core to validate request/response schemas
            endpoint_key = f"{method.upper()} {path}"

            # Check if endpoint exists in spec
            path_item = self.spec.get("paths", {}).get(path)
            if not path_item:
                self.results["failures"].append(
                    {
                        "endpoint": endpoint_key,
                        "error": "Endpoint not found in specification",
                    }
                )
                self.results["endpoints_failed"] += 1
                return False

            method_spec = path_item.get(method.lower())
            if not method_spec:
                self.results["failures"].append(
                    {
                        "endpoint": endpoint_key,
                        "error": f"Method {method} not defined in specification",
                    }
                )
                self.results["endpoints_failed"] += 1
                return False

            # Check if response status is defined in spec
            expected_responses = method_spec.get("responses", {})
            if str(response.status_code) not in expected_responses:
                self.results["failures"].append(
                    {
                        "endpoint": endpoint_key,
                        "error": f"Status {response.status_code} not in spec",
                        "status_code": response.status_code,
                    }
                )
                self.results["endpoints_failed"] += 1
                return False

            # Basic JSON validation for successful responses
            if response.status_code < 400:
                try:
                    response.json()
                except json.JSONDecodeError:
                    self.results["failures"].append(
                        {
                            "endpoint": endpoint_key,
                            "error": "Response is not valid JSON",
                        }
                    )
                    self.results["endpoints_failed"] += 1
                    return False

            self.results["endpoints_passed"] += 1
            return True

        except httpx.RequestError as e:
            self.results["failures"].append(
                {
                    "endpoint": f"{method.upper()} {path}",
                    "error": f"Request failed: {str(e)}",
                }
            )
            self.results["endpoints_failed"] += 1
            return False
        except Exception as e:
            self.results["failures"].append(
                {
                    "endpoint": f"{method.upper()} {path}",
                    "error": f"Unexpected error: {str(e)}",
                }
            )
            self.results["endpoints_failed"] += 1
            return False

    async def run_validation_suite(self, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Run full validation suite against all endpoints.

        Parameters
        ----------
        token : str, optional
            Bearer token for authenticated endpoints

        Returns
        -------
        Dict[str, Any]
            Validation results
        """
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Test authentication endpoints
        await self.validate_endpoint(
            "POST",
            "/auth/register",
            json_data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "testpass123",  # pragma: allowlist secret
            },
        )

        await self.validate_endpoint(
            "POST",
            "/auth/login",
            json_data={
                "email": "test@example.com",
                "password": "testpass123",  # pragma: allowlist secret
            },
        )

        # Test user endpoints (require auth)
        await self.validate_endpoint("GET", "/users/me", headers=headers)
        await self.validate_endpoint(
            "PUT",
            "/users/me",
            headers=headers,
            json_data={"full_name": "Test User"},  # pragma: allowlist secret
        )

        # Test project endpoints
        await self.validate_endpoint("GET", "/projects", headers=headers)
        await self.validate_endpoint(
            "POST",
            "/projects",
            headers=headers,
            json_data={"name": "Test Project", "description": "A test project"},
        )

        # Test task endpoints
        await self.validate_endpoint("GET", "/tasks", headers=headers)
        await self.validate_endpoint(
            "POST",
            "/tasks",
            headers=headers,
            json_data={
                "title": "Test Task",
                "project_id": "00000000-0000-0000-0000-000000000001",
            },
        )

        return self.results

    def generate_report(self) -> str:
        """
        Generate validation report.

        Returns
        -------
        str
            Formatted validation report
        """
        total = self.results["endpoints_tested"]
        passed = self.results["endpoints_passed"]
        failed = self.results["endpoints_failed"]

        compliance_rate = (passed / total * 100) if total > 0 else 0

        report = f"""
===========================================
API Validation Report
===========================================
Timestamp: {self.results['timestamp']}
Specification: {self.spec_path.name}

Endpoints Tested: {total}
Endpoints Passed: {passed}
Endpoints Failed: {failed}
Compliance Rate: {compliance_rate:.1f}%

"""
        if self.results["failures"]:
            report += "Failures:\n"
            report += "-" * 43 + "\n"
            for failure in self.results["failures"]:
                report += f"  {failure['endpoint']}\n"
                report += f"    Error: {failure['error']}\n\n"

        return report


class QualityMetrics:
    """Measures code quality metrics for the implementation."""

    def __init__(self, project_root: Path):
        """
        Initialize quality metrics.

        Parameters
        ----------
        project_root : Path
            Root directory of the implementation
        """
        self.project_root = project_root
        self.metrics: Dict[str, Any] = {}

    def measure_test_coverage(self) -> float:
        """
        Measure test coverage using pytest-cov.

        Returns
        -------
        float
            Coverage percentage
        """
        try:
            subprocess.run(
                ["pytest", "--cov=.", "--cov-report=json", "--cov-report=term"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Read coverage from json report
            cov_file = self.project_root / "coverage.json"
            if cov_file.exists():
                with open(cov_file, "r") as f:
                    cov_data = json.load(f)
                    percent_covered = cov_data.get("totals", {}).get(
                        "percent_covered", 0.0
                    )
                    coverage: float = float(percent_covered)
                    self.metrics["test_coverage"] = coverage
                    return coverage

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Coverage measurement failed: {e}")
            self.metrics["test_coverage"] = 0.0
            return 0.0

        return 0.0

    def check_type_safety(self) -> int:
        """
        Check type safety using mypy.

        Returns
        -------
        int
            Number of mypy errors
        """
        try:
            result = subprocess.run(
                ["mypy", ".", "--ignore-missing-imports"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Count errors in mypy output
            error_lines = [
                line for line in result.stdout.split("\n") if "error:" in line.lower()
            ]
            error_count = len(error_lines)
            self.metrics["mypy_errors"] = error_count
            return error_count

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Type checking failed: {e}")
            self.metrics["mypy_errors"] = -1
            return -1

    def generate_quality_report(self) -> str:
        """
        Generate quality metrics report.

        Returns
        -------
        str
            Formatted quality report
        """
        coverage = self.metrics.get("test_coverage", 0.0)
        mypy_errors = self.metrics.get("mypy_errors", -1)

        report = f"""
===========================================
Code Quality Report
===========================================
Test Coverage: {coverage:.1f}% {'✓' if coverage >= 80 else '✗'}
Type Safety: {mypy_errors} errors {'✓' if mypy_errors == 0 else '✗'}

Quality Benchmarks:
  Target Coverage: 80%
  Target Mypy Errors: 0
"""
        return report


async def main() -> None:
    """Run the complete validation and quality suite."""
    print("=" * 60)
    print("Marcus Multi-Agent Demo - API Validation Suite")
    print("=" * 60)

    # Configuration
    spec_path = Path(__file__).parent / "task_management_api_spec.yaml"
    base_url = "http://localhost:8000/api/v1"

    # Check if spec exists
    if not spec_path.exists():
        print(f"ERROR: Specification not found at {spec_path}")
        sys.exit(1)

    # Run API validation
    print("\n[1/3] Validating API endpoints...")
    validator = APIValidator(str(spec_path), base_url)

    try:
        await validator.run_validation_suite()
        print(validator.generate_report())
    except Exception as e:
        print(f"ERROR: API validation failed: {e}")
        print("\nNote: Ensure the API server is running at", base_url)

    # Measure quality metrics (if implementation exists)
    impl_root = Path(__file__).parent / "implementation"
    if impl_root.exists():
        print("\n[2/3] Measuring test coverage...")
        print("[3/3] Checking type safety...")

        metrics = QualityMetrics(impl_root)
        metrics.measure_test_coverage()
        metrics.check_type_safety()
        print(metrics.generate_quality_report())
    else:
        print("\n[2/3] Skipping quality metrics - implementation not found")
        print(f"      Expected at: {impl_root}")

    # Summary
    print("\n" + "=" * 60)
    print("Validation Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
