#!/usr/bin/env python3
"""
Test script for calcus.ru API rate limiting and error handling.
This script tests the enhanced rate limiting and retry logic.
"""
import sys
import time
import threading
import concurrent.futures
from datetime import datetime

# Import our utils function
from utils import get_customs_fees_russia


def test_single_request():
    """Test a single API request"""
    print("🧪 Testing single API request...")

    result = get_customs_fees_russia(
        engine_volume=2000,
        car_price=15000000,
        car_year=2020,
        car_month=6,
        engine_type=1
    )

    if result is None:
        print("❌ Single request failed")
        return False

    if all(key in result for key in ["sbor", "tax", "util"]):
        print("✅ Single request successful")
        print(f"   Response keys: {list(result.keys())}")
        return True
    else:
        print(f"❌ Single request returned incomplete data: {result}")
        return False


def test_sequential_requests(count=5):
    """Test sequential requests to verify rate limiting"""
    print(f"\n🧪 Testing {count} sequential requests...")

    start_time = time.time()
    successful_requests = 0

    for i in range(count):
        print(f"   Request {i+1}/{count}...")
        result = get_customs_fees_russia(
            engine_volume=2000 + (i * 100),  # Vary parameters slightly
            car_price=15000000 + (i * 100000),
            car_year=2020,
            car_month=6,
            engine_type=1
        )

        if result is not None:
            successful_requests += 1
            print(f"   ✅ Request {i+1} successful")
        else:
            print(f"   ❌ Request {i+1} failed")

    end_time = time.time()
    duration = end_time - start_time

    print(f"Sequential test results:")
    print(f"   Successful: {successful_requests}/{count}")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Average time per request: {duration/count:.2f} seconds")

    return successful_requests == count


def single_threaded_request(thread_id, results):
    """Single threaded request for concurrent testing"""
    try:
        result = get_customs_fees_russia(
            engine_volume=2000 + (thread_id * 50),
            car_price=15000000 + (thread_id * 50000),
            car_year=2020,
            car_month=6,
            engine_type=1
        )

        if result is not None:
            results[thread_id] = True
            print(f"   ✅ Thread {thread_id} successful")
        else:
            results[thread_id] = False
            print(f"   ❌ Thread {thread_id} failed")

    except Exception as e:
        results[thread_id] = False
        print(f"   ❌ Thread {thread_id} exception: {e}")


def test_concurrent_requests(count=3):
    """Test concurrent requests to verify thread safety"""
    print(f"\n🧪 Testing {count} concurrent requests...")

    results = {}
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [
            executor.submit(single_threaded_request, i, results)
            for i in range(count)
        ]

        # Wait for all threads to complete
        concurrent.futures.wait(futures)

    end_time = time.time()
    duration = end_time - start_time

    successful_requests = sum(1 for success in results.values() if success)

    print(f"Concurrent test results:")
    print(f"   Successful: {successful_requests}/{count}")
    print(f"   Duration: {duration:.2f} seconds")

    return successful_requests == count


def test_error_handling():
    """Test error handling with invalid parameters"""
    print(f"\n🧪 Testing error handling...")

    # Test with invalid engine volume (should still work due to API tolerance)
    result1 = get_customs_fees_russia(
        engine_volume=999999,  # Very large engine
        car_price=15000000,
        car_year=2020,
        car_month=6,
        engine_type=1
    )

    # Test with very old car
    result2 = get_customs_fees_russia(
        engine_volume=2000,
        car_price=15000000,
        car_year=1990,
        car_month=1,
        engine_type=1
    )

    print(f"   Large engine test: {'✅ Success' if result1 else '❌ Failed'}")
    print(f"   Old car test: {'✅ Success' if result2 else '❌ Failed'}")

    return True  # Error handling tests pass if they don't crash


def run_full_test_suite():
    """Run the complete test suite"""
    print("=" * 60)
    print("🚀 Starting calcus.ru API Test Suite")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("Single Request", test_single_request),
        ("Sequential Requests", lambda: test_sequential_requests(5)),
        ("Concurrent Requests", lambda: test_concurrent_requests(3)),
        ("Error Handling", test_error_handling),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\n{'='*40}")
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
        except Exception as e:
            print(f"{test_name}: ❌ EXCEPTION - {e}")
            results.append((test_name, False))

    # Final summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The calcus.ru API fix is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    try:
        success = run_full_test_suite()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Test suite crashed: {e}")
        sys.exit(1)