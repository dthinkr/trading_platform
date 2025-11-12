#!/usr/bin/env python3
"""
Trading Platform Stress Test
Tests platform performance under various load conditions
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import List, Dict
import statistics


class StressTestMetrics:
    """Collect and store stress test metrics"""
    
    def __init__(self):
        self.login_times = []
        self.start_trading_times = []
        self.total_users = 0
        self.successful_logins = 0
        self.failed_logins = 0
        self.markets_created = 0
        self.concurrent_sessions = 0
        self.start_time = None
        self.end_time = None
        self.errors = []
        
    def add_login_time(self, duration: float):
        self.login_times.append(duration)
        
    def add_start_trading_time(self, duration: float):
        self.start_trading_times.append(duration)
        
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        return {
            'total_users': self.total_users,
            'successful_logins': self.successful_logins,
            'failed_logins': self.failed_logins,
            'success_rate': (self.successful_logins / self.total_users * 100) if self.total_users > 0 else 0,
            'avg_login_time': statistics.mean(self.login_times) if self.login_times else 0,
            'median_login_time': statistics.median(self.login_times) if self.login_times else 0,
            'max_login_time': max(self.login_times) if self.login_times else 0,
            'min_login_time': min(self.login_times) if self.login_times else 0,
            'avg_start_trading_time': statistics.mean(self.start_trading_times) if self.start_trading_times else 0,
            'markets_created': self.markets_created,
            'concurrent_sessions': self.concurrent_sessions,
            'total_duration': (self.end_time - self.start_time) if self.start_time and self.end_time else 0,
            'throughput': self.successful_logins / (self.end_time - self.start_time) if self.start_time and self.end_time else 0,
            'errors': len(self.errors)
        }


async def login_user(session: aiohttp.ClientSession, user_id: int, backend_url: str, metrics: StressTestMetrics):
    """Login a single user and measure time"""
    start = time.time()
    
    try:
        url = f"{backend_url}/user/login"
        params = {
            "PROLIFIC_PID": f"stresstest_user{user_id}",
            "STUDY_ID": "stress_test",
            "SESSION_ID": f"stress_session{user_id}"
        }
        data = {
            "username": "user1",
            "password": "password1"
        }
        
        async with session.post(url, params=params, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
            duration = time.time() - start
            metrics.add_login_time(duration)
            
            if response.status == 200:
                result = await response.json()
                metrics.successful_logins += 1
                return {
                    'success': True,
                    'user_id': user_id,
                    'data': result.get('data', {}),
                    'duration': duration
                }
            else:
                metrics.failed_logins += 1
                metrics.errors.append(f"User {user_id}: HTTP {response.status}")
                return {
                    'success': False,
                    'user_id': user_id,
                    'error': f"HTTP {response.status}",
                    'duration': duration
                }
    except Exception as e:
        duration = time.time() - start
        metrics.failed_logins += 1
        metrics.errors.append(f"User {user_id}: {str(e)}")
        return {
            'success': False,
            'user_id': user_id,
            'error': str(e),
            'duration': duration
        }


async def start_trading(session: aiohttp.ClientSession, user_data: Dict, backend_url: str, metrics: StressTestMetrics):
    """Mark user as ready to start trading"""
    start = time.time()
    
    try:
        prolific_pid = user_data['data'].get('trader_id', '').replace('HUMAN_', '')
        url = f"{backend_url}/trading/start"
        params = {
            "PROLIFIC_PID": prolific_pid,
            "STUDY_ID": "stress_test",
            "SESSION_ID": f"stress_session{user_data['user_id']}"
        }
        data = {
            "username": "user1",
            "password": "password1"
        }
        
        async with session.post(url, params=params, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
            duration = time.time() - start
            metrics.add_start_trading_time(duration)
            
            if response.status == 200:
                result = await response.json()
                return {
                    'success': True,
                    'all_ready': result.get('all_ready', False),
                    'duration': duration
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status}",
                    'duration': duration
                }
    except Exception as e:
        duration = time.time() - start
        return {
            'success': False,
            'error': str(e),
            'duration': duration
        }


async def run_stress_test(num_users: int, backend_url: str = "http://localhost:8000", batch_size: int = 10):
    """
    Run stress test with specified number of users
    
    Args:
        num_users: Total number of users to simulate
        backend_url: Backend URL
        batch_size: Number of concurrent requests per batch
    """
    print(f"\n{'='*70}")
    print(f"STRESS TEST: {num_users} users, batch size: {batch_size}")
    print(f"{'='*70}\n")
    
    metrics = StressTestMetrics()
    metrics.total_users = num_users
    metrics.start_time = time.time()
    
    # Create session
    connector = aiohttp.TCPConnector(limit=batch_size * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        
        # Phase 1: Login all users in batches
        print("Phase 1: Logging in users...")
        all_user_data = []
        
        for batch_start in range(0, num_users, batch_size):
            batch_end = min(batch_start + batch_size, num_users)
            batch_users = range(batch_start + 1, batch_end + 1)
            
            tasks = [login_user(session, user_id, backend_url, metrics) for user_id in batch_users]
            results = await asyncio.gather(*tasks)
            
            successful_users = [r for r in results if r['success']]
            all_user_data.extend(successful_users)
            
            print(f"  Batch {batch_start//batch_size + 1}: {len(successful_users)}/{len(batch_users)} successful")
            
            # Small delay between batches
            if batch_end < num_users:
                await asyncio.sleep(0.5)
        
        print(f"\n✓ Login complete: {len(all_user_data)}/{num_users} users logged in")
        if metrics.login_times:
            print(f"  Avg login time: {statistics.mean(metrics.login_times):.3f}s")
        else:
            print(f"  No successful logins to calculate average time")
        
        # Phase 2: Start trading for all users in batches
        print("\nPhase 2: Starting trading...")
        
        for batch_start in range(0, len(all_user_data), batch_size):
            batch_end = min(batch_start + batch_size, len(all_user_data))
            batch_users = all_user_data[batch_start:batch_end]
            
            tasks = [start_trading(session, user_data, backend_url, metrics) for user_data in batch_users]
            results = await asyncio.gather(*tasks)
            
            successful_starts = len([r for r in results if r['success']])
            markets_started = len([r for r in results if r.get('all_ready', False)])
            
            print(f"  Batch {batch_start//batch_size + 1}: {successful_starts}/{len(batch_users)} started, {markets_started} markets ready")
            
            if batch_end < len(all_user_data):
                await asyncio.sleep(0.5)
        
        print(f"\n✓ Trading start complete")
        if metrics.start_trading_times:
            print(f"  Avg start time: {statistics.mean(metrics.start_trading_times):.3f}s")
        else:
            print(f"  No trading starts to calculate average time")
    
    metrics.end_time = time.time()
    
    # Get final statistics
    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    
    summary = metrics.get_summary()
    print(f"Total users:           {summary['total_users']}")
    print(f"Successful logins:     {summary['successful_logins']}")
    print(f"Failed logins:         {summary['failed_logins']}")
    print(f"Success rate:          {summary['success_rate']:.1f}%")
    print(f"\nPerformance:")
    print(f"  Avg login time:      {summary['avg_login_time']:.3f}s")
    print(f"  Median login time:   {summary['median_login_time']:.3f}s")
    print(f"  Min login time:      {summary['min_login_time']:.3f}s")
    print(f"  Max login time:      {summary['max_login_time']:.3f}s")
    print(f"  Total duration:      {summary['total_duration']:.2f}s")
    print(f"  Throughput:          {summary['throughput']:.1f} users/sec")
    print(f"\nErrors:                {summary['errors']}")
    
    return summary, metrics


async def run_multiple_tests(test_configs: List[Dict], backend_url: str = "http://localhost:8000"):
    """
    Run multiple stress tests with different configurations
    
    Args:
        test_configs: List of test configurations, each with 'num_users' and 'batch_size'
    """
    results = []
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n\n{'#'*70}")
        print(f"# TEST {i}/{len(test_configs)}")
        print(f"{'#'*70}")
        
        summary, metrics = await run_stress_test(
            num_users=config['num_users'],
            backend_url=backend_url,
            batch_size=config.get('batch_size', 10)
        )
        
        results.append({
            'config': config,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        })
        
        # Wait between tests to let system stabilize
        if i < len(test_configs):
            print("\nWaiting 5 seconds before next test...")
            await asyncio.sleep(5)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"stress_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n\n{'='*70}")
    print(f"ALL TESTS COMPLETE")
    print(f"Results saved to: {results_file}")
    print(f"{'='*70}\n")
    
    return results, results_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Stress test the trading platform")
    parser.add_argument("--users", type=int, default=20, help="Number of users to simulate")
    parser.add_argument("--batch-size", type=int, default=10, help="Concurrent requests per batch")
    parser.add_argument("--backend", type=str, default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--multi-test", action="store_true", help="Run multiple tests with increasing load")
    
    args = parser.parse_args()
    
    if args.multi_test:
        # Run multiple tests with increasing load
        test_configs = [
            {'num_users': 5, 'batch_size': 5},
            {'num_users': 10, 'batch_size': 10},
            {'num_users': 20, 'batch_size': 10},
            {'num_users': 50, 'batch_size': 20},
            {'num_users': 100, 'batch_size': 25},
        ]
        asyncio.run(run_multiple_tests(test_configs, args.backend))
    else:
        # Single test
        asyncio.run(run_stress_test(args.users, args.backend, args.batch_size))

