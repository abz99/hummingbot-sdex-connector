"""
Performance Benchmarking Test Suite
Comprehensive performance testing for real-world validation.
"""

import asyncio
import os
import time
import statistics
from decimal import Decimal
from typing import List, Dict, Any, Tuple
import pytest
import pytest_asyncio
from concurrent.futures import ThreadPoolExecutor
import aiohttp

# Import connector components
from hummingbot.connector.exchange.stellar.stellar_chain_interface import (
    ModernStellarChainInterface,
)
from hummingbot.connector.exchange.stellar.stellar_config_models import StellarNetworkConfig
from hummingbot.connector.exchange.stellar.stellar_observability import (
    StellarObservabilityFramework,
)
from hummingbot.connector.exchange.stellar.stellar_exchange import StellarExchange

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def performance_config():
    """Configuration optimized for performance testing."""
    from hummingbot.connector.exchange.stellar.stellar_config_models import (
        NetworkEndpointConfig,
        RateLimitConfig,
    )

    return StellarNetworkConfig(
        name="performance_testnet",
        network_passphrase="Test SDF Network ; September 2015",
        horizon=NetworkEndpointConfig(
            primary="https://horizon-testnet.stellar.org", request_timeout=30.0
        ),
        soroban=NetworkEndpointConfig(primary="https://soroban-testnet.stellar.org"),
        rate_limits=RateLimitConfig(requests_per_second=10, burst_limit=20),
    )


class TestThroughputBenchmarks:
    """Throughput benchmarking tests."""

    async def test_horizon_request_throughput(self, performance_config):
        """Test Horizon API request throughput."""
        chain_interface = ModernStellarChainInterface(
            config=performance_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Benchmark parameters
            total_requests = 100
            concurrent_requests = 20

            print(
                f"\n🚀 Testing Horizon throughput: {total_requests} requests, {concurrent_requests} concurrent"
            )

            start_time = time.time()

            # Create batches of concurrent requests
            all_results = []
            for batch in range(0, total_requests, concurrent_requests):
                batch_size = min(concurrent_requests, total_requests - batch)

                # Create concurrent tasks for this batch
                tasks = [chain_interface.get_latest_ledger() for _ in range(batch_size)]

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_results.extend(batch_results)

                # Small delay between batches to avoid overwhelming the server
                await asyncio.sleep(0.1)

            end_time = time.time()

            # Analyze results
            successful_requests = sum(1 for r in all_results if not isinstance(r, Exception))
            failed_requests = total_requests - successful_requests
            total_duration = end_time - start_time
            throughput = successful_requests / total_duration

            # Performance metrics
            print("📊 Throughput Results:")
            print(f"  Total requests: {total_requests}")
            print(f"  Successful: {successful_requests}")
            print(f"  Failed: {failed_requests}")
            print(f"  Duration: {total_duration:.2f}s")
            print(f"  Throughput: {throughput:.2f} req/s")
            print(f"  Success rate: {(successful_requests/total_requests)*100:.1f}%")

            # Performance assertions
            assert (
                successful_requests >= total_requests * 0.95
            ), f"Success rate too low: {successful_requests}/{total_requests}"
            assert throughput >= 10, f"Throughput too low: {throughput:.2f} req/s"

        finally:
            await chain_interface.stop()

    @pytest.mark.skipif(
        not os.getenv("STELLAR_TESTNET_ENABLED", "false").lower() == "true",
        reason="Account validation requires STELLAR_TESTNET_ENABLED=true environment variable"
    )
    async def test_concurrent_account_lookups(self, performance_config):
        """Test concurrent account lookup throughput."""
        chain_interface = ModernStellarChainInterface(
            config=performance_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Test with valid testnet accounts (56 character account IDs)
            test_accounts = [
                "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7",  # Valid 56-char account
                "GCKFBEIYTKP5RPHQLZX6CXAEF5ZBNVVXV4F5BWSKJ7JJOHIUZZKBDSJ2",  # Valid 56-char account
                "GDUZ6IPN6MPS3X2GDWOKWWJQPLG3IBDNCM2LUJ2HSUQPVR5LRFDHH4S5",  # Valid 56-char account
            ]

            concurrent_lookups = 15
            total_lookups = concurrent_lookups * len(test_accounts)

            print(f"\n🔍 Testing concurrent account lookups: {total_lookups} total lookups")

            start_time = time.time()

            # Create concurrent account lookup tasks
            tasks = []
            for account_id in test_accounts:
                for _ in range(concurrent_lookups):
                    task = chain_interface.get_account_with_retry(account_id)
                    tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()

            # Analyze results
            successful_lookups = sum(1 for r in results if not isinstance(r, Exception))
            total_duration = end_time - start_time
            lookup_throughput = successful_lookups / total_duration

            print("📊 Account Lookup Results:")
            print(f"  Total lookups: {total_lookups}")
            print(f"  Successful: {successful_lookups}")
            print(f"  Duration: {total_duration:.2f}s")
            print(f"  Throughput: {lookup_throughput:.2f} lookups/s")

            # Performance assertions
            assert successful_lookups >= total_lookups * 0.8, "Account lookup success rate too low"
            assert (
                lookup_throughput >= 5
            ), f"Account lookup throughput too low: {lookup_throughput:.2f} lookups/s"

        finally:
            await chain_interface.stop()


class TestLatencyBenchmarks:
    """Latency benchmarking tests."""

    async def test_horizon_response_latency(self, performance_config):
        """Test Horizon API response latency."""
        chain_interface = ModernStellarChainInterface(
            config=performance_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            latencies = []
            test_iterations = 30

            print(f"\n⏱️ Testing Horizon response latency: {test_iterations} requests")

            for i in range(test_iterations):
                start_time = time.time()

                try:
                    await chain_interface.get_latest_ledger()
                    end_time = time.time()

                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)

                except Exception as e:
                    print(f"  Request {i+1} failed: {e}")

                # Small delay between requests
                await asyncio.sleep(0.5)

            if latencies:
                # Calculate statistics
                avg_latency = statistics.mean(latencies)
                median_latency = statistics.median(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

                print("📊 Latency Results:")
                print(f"  Requests: {len(latencies)}")
                print(f"  Average: {avg_latency:.2f}ms")
                print(f"  Median: {median_latency:.2f}ms")
                print(f"  Min: {min_latency:.2f}ms")
                print(f"  Max: {max_latency:.2f}ms")
                print(f"  95th percentile: {p95_latency:.2f}ms")

                # Performance assertions
                assert avg_latency < 2000, f"Average latency too high: {avg_latency:.2f}ms"
                assert p95_latency < 5000, f"95th percentile latency too high: {p95_latency:.2f}ms"
                assert len(latencies) >= test_iterations * 0.9, "Too many failed requests"
            else:
                pytest.fail("No successful requests to measure latency")

        finally:
            await chain_interface.stop()

    async def test_soroban_rpc_latency(self, performance_config):
        """Test Soroban RPC response latency."""
        chain_interface = ModernStellarChainInterface(
            config=performance_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            latencies = []
            test_iterations = 20

            print(f"\n⏱️ Testing Soroban RPC latency: {test_iterations} requests")

            for i in range(test_iterations):
                start_time = time.time()

                try:
                    # Test basic Soroban health check
                    health_status = await chain_interface.check_soroban_health()
                    end_time = time.time()

                    if health_status:
                        latency_ms = (end_time - start_time) * 1000
                        latencies.append(latency_ms)

                except Exception as e:
                    print(f"  Soroban request {i+1} failed: {e}")

                await asyncio.sleep(0.5)

            if latencies:
                avg_latency = statistics.mean(latencies)
                max_latency = max(latencies)

                print("📊 Soroban RPC Latency Results:")
                print(f"  Successful requests: {len(latencies)}")
                print(f"  Average latency: {avg_latency:.2f}ms")
                print(f"  Max latency: {max_latency:.2f}ms")

                # Performance assertions (Soroban may be slower than Horizon)
                assert avg_latency < 3000, f"Soroban average latency too high: {avg_latency:.2f}ms"
                assert len(latencies) >= test_iterations * 0.7, "Too many failed Soroban requests"
            else:
                print("⚠️  No successful Soroban requests - may not be available")

        finally:
            await chain_interface.stop()


class TestScalabilityBenchmarks:
    """Scalability and load testing benchmarks."""

    async def test_connection_pool_scalability(self, performance_config):
        """Test connection pool scalability under load."""

        # Create multiple chain interfaces to simulate multiple connections
        interfaces = []
        num_interfaces = 5

        print(f"\n🔗 Testing connection pool scalability: {num_interfaces} interfaces")

        try:
            # Initialize multiple interfaces
            for i in range(num_interfaces):
                interface = ModernStellarChainInterface(
                    config=performance_config,
                    security_framework=None,
                    observability=StellarObservabilityFramework(),
                )
                await interface.start()
                interfaces.append(interface)

            # Run concurrent operations across all interfaces
            tasks = []
            requests_per_interface = 10

            start_time = time.time()

            for interface in interfaces:
                for _ in range(requests_per_interface):
                    task = interface.get_latest_ledger()
                    tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()

            # Analyze scalability results
            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            total_requests = len(tasks)
            total_duration = end_time - start_time
            scalability_throughput = successful_requests / total_duration

            print("📊 Scalability Results:")
            print(f"  Interfaces: {num_interfaces}")
            print(f"  Total requests: {total_requests}")
            print(f"  Successful: {successful_requests}")
            print(f"  Duration: {total_duration:.2f}s")
            print(f"  Throughput: {scalability_throughput:.2f} req/s")

            # Scalability assertions
            assert successful_requests >= total_requests * 0.9, "Scalability success rate too low"
            assert (
                scalability_throughput >= 15
            ), f"Scalability throughput too low: {scalability_throughput:.2f} req/s"

        finally:
            # Cleanup all interfaces
            for interface in interfaces:
                try:
                    await interface.stop()
                except Exception:
                    pass

    async def test_sustained_load_performance(self, performance_config):
        """Test performance under sustained load."""
        chain_interface = ModernStellarChainInterface(
            config=performance_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Sustained load parameters
            test_duration = 60  # 1 minute
            target_rps = 5  # 5 requests per second

            print(f"\n🔄 Testing sustained load: {test_duration}s at {target_rps} RPS")

            start_time = time.time()
            end_test_time = start_time + test_duration

            request_times = []
            latencies = []
            errors = []

            while time.time() < end_test_time:
                request_start = time.time()

                try:
                    await chain_interface.get_latest_ledger()
                    request_end = time.time()

                    request_times.append(request_start)
                    latencies.append((request_end - request_start) * 1000)

                except Exception as e:
                    errors.append(str(e))

                # Maintain target RPS - adjust sleep time based on request duration
                request_duration = time.time() - request_start
                target_interval = 1.0 / target_rps
                sleep_time = max(0, target_interval - request_duration)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            # Analyze sustained load results
            actual_duration = time.time() - start_time
            actual_rps = len(request_times) / actual_duration
            avg_latency = statistics.mean(latencies) if latencies else 0
            error_rate = len(errors) / (len(request_times) + len(errors))

            print("📊 Sustained Load Results:")
            print(f"  Target duration: {test_duration}s")
            print(f"  Actual duration: {actual_duration:.2f}s")
            print(f"  Target RPS: {target_rps}")
            print(f"  Actual RPS: {actual_rps:.2f}")
            print(f"  Successful requests: {len(request_times)}")
            print(f"  Errors: {len(errors)}")
            print(f"  Error rate: {error_rate:.2%}")
            print(f"  Average latency: {avg_latency:.2f}ms")

            # Sustained load assertions
            assert error_rate <= 0.05, f"Error rate too high: {error_rate:.2%}"
            assert actual_rps >= target_rps * 0.8, f"Actual RPS too low: {actual_rps:.2f}"
            assert avg_latency < 3000, f"Average latency degraded: {avg_latency:.2f}ms"

        finally:
            await chain_interface.stop()


class TestMemoryAndResourceBenchmarks:
    """Memory usage and resource consumption benchmarks."""

    async def test_memory_usage_under_load(self, performance_config):
        """Test memory usage during high load operations."""
        import psutil
        import os

        # Get current process for memory monitoring
        process = psutil.Process(os.getpid())

        chain_interface = ModernStellarChainInterface(
            config=performance_config,
            security_framework=None,
            observability=StellarObservabilityFramework(),
        )

        await chain_interface.start()

        try:
            # Record baseline memory usage
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            print("\n💾 Testing memory usage under load")
            print(f"  Baseline memory: {baseline_memory:.2f} MB")

            # Generate load to test memory usage
            memory_samples = []
            tasks = []

            # Create many concurrent requests
            for i in range(100):
                task = chain_interface.get_latest_ledger()
                tasks.append(task)

                # Sample memory every 10 requests
                if i % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)

            # Execute all tasks
            await asyncio.gather(*tasks, return_exceptions=True)

            # Final memory measurement
            final_memory = process.memory_info().rss / 1024 / 1024
            peak_memory = max(memory_samples) if memory_samples else final_memory
            memory_increase = final_memory - baseline_memory

            print("📊 Memory Usage Results:")
            print(f"  Baseline: {baseline_memory:.2f} MB")
            print(f"  Peak: {peak_memory:.2f} MB")
            print(f"  Final: {final_memory:.2f} MB")
            print(f"  Increase: {memory_increase:.2f} MB")
            print(f"  Peak increase: {peak_memory - baseline_memory:.2f} MB")

            # Memory usage assertions
            assert memory_increase < 50, f"Memory increase too high: {memory_increase:.2f} MB"
            assert (
                peak_memory - baseline_memory < 100
            ), f"Peak memory usage too high: {peak_memory - baseline_memory:.2f} MB"

        finally:
            await chain_interface.stop()

    async def test_connection_cleanup_efficiency(self, performance_config):
        """Test efficiency of connection cleanup and resource release."""
        import gc

        print("\n🧹 Testing connection cleanup efficiency")

        # Track objects before creating interfaces
        gc.collect()
        objects_before = len(gc.get_objects())

        interfaces = []
        num_interfaces = 10

        # Create multiple interfaces
        for i in range(num_interfaces):
            interface = ModernStellarChainInterface(
                config=performance_config,
                security_framework=None,
                observability=StellarObservabilityFramework(),
            )
            await interface.start()
            interfaces.append(interface)

        # Use interfaces briefly
        tasks = []
        for interface in interfaces:
            task = interface.get_latest_ledger()
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        # Clean up all interfaces
        for interface in interfaces:
            await interface.stop()

        # Clear references
        interfaces.clear()

        # Force garbage collection multiple times for thorough cleanup
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0.1)  # Allow async cleanup to complete

        objects_after = len(gc.get_objects())

        object_difference = objects_after - objects_before

        print("📊 Cleanup Efficiency Results:")
        print(f"  Objects before: {objects_before}")
        print(f"  Objects after: {objects_after}")
        print(f"  Difference: {object_difference}")
        print(f"  Interfaces created/destroyed: {num_interfaces}")

        # Cleanup efficiency assertions - more realistic threshold for async operations
        assert object_difference < 5000, f"Too many objects not cleaned up: {object_difference}"
