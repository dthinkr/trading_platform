#!/usr/bin/env python3
"""
Visualize stress test results
Creates charts showing platform performance under load
"""

import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
from datetime import datetime
from pathlib import Path
import glob


def load_results(results_file: str = None):
    """Load stress test results from JSON file"""
    if results_file is None:
        # Find most recent results file
        results_files = sorted(glob.glob("stress_test_results_*.json"), reverse=True)
        if not results_files:
            raise FileNotFoundError("No stress test results found")
        results_file = results_files[0]
        print(f"Loading results from: {results_file}")
    
    with open(results_file, 'r') as f:
        return json.load(f), results_file


def create_performance_charts(results, output_prefix="stress_test"):
    """Create comprehensive performance charts"""
    
    # Extract data
    num_users_list = [r['config']['num_users'] for r in results]
    success_rates = [r['summary']['success_rate'] for r in results]
    avg_login_times = [r['summary']['avg_login_time'] for r in results]
    median_login_times = [r['summary']['median_login_time'] for r in results]
    max_login_times = [r['summary']['max_login_time'] for r in results]
    throughputs = [r['summary']['throughput'] for r in results]
    total_durations = [r['summary']['total_duration'] for r in results]
    error_counts = [r['summary']['errors'] for r in results]
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    
    # 1. Success Rate vs Number of Users
    ax1 = plt.subplot(3, 3, 1)
    ax1.plot(num_users_list, success_rates, marker='o', linewidth=2, markersize=8, color='#2ecc71')
    ax1.set_xlabel('Number of Users', fontsize=12)
    ax1.set_ylabel('Success Rate (%)', fontsize=12)
    ax1.set_title('Login Success Rate', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 105])
    for i, (x, y) in enumerate(zip(num_users_list, success_rates)):
        ax1.annotate(f'{y:.1f}%', (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=9)
    
    # 2. Average Login Time vs Number of Users
    ax2 = plt.subplot(3, 3, 2)
    ax2.plot(num_users_list, avg_login_times, marker='s', linewidth=2, markersize=8, color='#3498db', label='Average')
    ax2.plot(num_users_list, median_login_times, marker='^', linewidth=2, markersize=8, color='#9b59b6', label='Median')
    ax2.set_xlabel('Number of Users', fontsize=12)
    ax2.set_ylabel('Login Time (seconds)', fontsize=12)
    ax2.set_title('Login Response Time', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 3. Throughput vs Number of Users
    ax3 = plt.subplot(3, 3, 3)
    ax3.plot(num_users_list, throughputs, marker='D', linewidth=2, markersize=8, color='#e74c3c')
    ax3.set_xlabel('Number of Users', fontsize=12)
    ax3.set_ylabel('Throughput (users/sec)', fontsize=12)
    ax3.set_title('Platform Throughput', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    for i, (x, y) in enumerate(zip(num_users_list, throughputs)):
        ax3.annotate(f'{y:.1f}', (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=9)
    
    # 4. Total Duration vs Number of Users
    ax4 = plt.subplot(3, 3, 4)
    ax4.bar(num_users_list, total_durations, color='#f39c12', alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Number of Users', fontsize=12)
    ax4.set_ylabel('Total Duration (seconds)', fontsize=12)
    ax4.set_title('Total Test Duration', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    for i, (x, y) in enumerate(zip(num_users_list, total_durations)):
        ax4.text(x, y, f'{y:.1f}s', ha='center', va='bottom', fontsize=9)
    
    # 5. Error Count vs Number of Users
    ax5 = plt.subplot(3, 3, 5)
    ax5.bar(num_users_list, error_counts, color='#e74c3c', alpha=0.7, edgecolor='black')
    ax5.set_xlabel('Number of Users', fontsize=12)
    ax5.set_ylabel('Number of Errors', fontsize=12)
    ax5.set_title('Error Count', fontsize=14, fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')
    for i, (x, y) in enumerate(zip(num_users_list, error_counts)):
        if y > 0:
            ax5.text(x, y, str(y), ha='center', va='bottom', fontsize=9)
    
    # 6. Login Time Distribution (Box plot style)
    ax6 = plt.subplot(3, 3, 6)
    login_time_data = []
    for r in results:
        login_time_data.append([
            r['summary']['min_login_time'],
            r['summary']['median_login_time'],
            r['summary']['max_login_time']
        ])
    
    for i, (users, times) in enumerate(zip(num_users_list, login_time_data)):
        ax6.plot([users, users], [times[0], times[2]], 'k-', linewidth=2)
        ax6.plot(users, times[0], 'go', markersize=8, label='Min' if i == 0 else '')
        ax6.plot(users, times[1], 'bs', markersize=8, label='Median' if i == 0 else '')
        ax6.plot(users, times[2], 'r^', markersize=8, label='Max' if i == 0 else '')
    
    ax6.set_xlabel('Number of Users', fontsize=12)
    ax6.set_ylabel('Login Time (seconds)', fontsize=12)
    ax6.set_title('Login Time Range (Min/Median/Max)', fontsize=14, fontweight='bold')
    ax6.legend(fontsize=10)
    ax6.grid(True, alpha=0.3)
    
    # 7. Scalability Chart (Users vs Duration - Linear vs Actual)
    ax7 = plt.subplot(3, 3, 7)
    # Calculate ideal linear scaling
    if len(num_users_list) > 0:
        base_duration = total_durations[0]
        base_users = num_users_list[0]
        ideal_durations = [base_duration * (users / base_users) for users in num_users_list]
        
        ax7.plot(num_users_list, total_durations, marker='o', linewidth=2, markersize=8, 
                color='#e74c3c', label='Actual')
        ax7.plot(num_users_list, ideal_durations, linestyle='--', linewidth=2, 
                color='#95a5a6', label='Linear Scaling')
        ax7.set_xlabel('Number of Users', fontsize=12)
        ax7.set_ylabel('Duration (seconds)', fontsize=12)
        ax7.set_title('Scalability Analysis', fontsize=14, fontweight='bold')
        ax7.legend(fontsize=10)
        ax7.grid(True, alpha=0.3)
    
    # 8. Success/Failure Breakdown
    ax8 = plt.subplot(3, 3, 8)
    successful_logins = [r['summary']['successful_logins'] for r in results]
    failed_logins = [r['summary']['failed_logins'] for r in results]
    
    x = np.arange(len(num_users_list))
    width = 0.35
    
    ax8.bar(x, successful_logins, width, label='Successful', color='#2ecc71', alpha=0.7, edgecolor='black')
    ax8.bar(x, failed_logins, width, bottom=successful_logins, label='Failed', 
           color='#e74c3c', alpha=0.7, edgecolor='black')
    
    ax8.set_xlabel('Test Number', fontsize=12)
    ax8.set_ylabel('Number of Users', fontsize=12)
    ax8.set_title('Login Success/Failure Breakdown', fontsize=14, fontweight='bold')
    ax8.set_xticks(x)
    ax8.set_xticklabels([f'{n} users' for n in num_users_list])
    ax8.legend(fontsize=10)
    ax8.grid(True, alpha=0.3, axis='y')
    
    # 9. Summary Statistics Table
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')
    
    # Create summary table
    summary_data = []
    summary_data.append(['Metric', 'Value'])
    summary_data.append(['Total Tests', str(len(results))])
    summary_data.append(['Max Users Tested', str(max(num_users_list))])
    summary_data.append(['Avg Success Rate', f"{np.mean(success_rates):.1f}%"])
    summary_data.append(['Avg Throughput', f"{np.mean(throughputs):.1f} users/s"])
    summary_data.append(['Max Throughput', f"{max(throughputs):.1f} users/s"])
    summary_data.append(['Total Errors', str(sum(error_counts))])
    
    table = ax9.table(cellText=summary_data, cellLoc='left', loc='center',
                     colWidths=[0.5, 0.5])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    
    # Style header row
    for i in range(2):
        table[(0, i)].set_facecolor('#34495e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Alternate row colors
    for i in range(1, len(summary_data)):
        for j in range(2):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#ecf0f1')
    
    ax9.set_title('Test Summary', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # Save figure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_prefix}_charts_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Charts saved to: {output_file}")
    
    return output_file


def create_summary_report(results, output_prefix="stress_test"):
    """Create text summary report"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_prefix}_report_{timestamp}.txt"
    
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("TRADING PLATFORM STRESS TEST REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Tests: {len(results)}\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"\n{'='*80}\n")
            f.write(f"TEST {i}: {result['config']['num_users']} Users\n")
            f.write(f"{'='*80}\n\n")
            
            summary = result['summary']
            f.write(f"Configuration:\n")
            f.write(f"  Users:              {result['config']['num_users']}\n")
            f.write(f"  Batch Size:         {result['config'].get('batch_size', 'N/A')}\n\n")
            
            f.write(f"Results:\n")
            f.write(f"  Success Rate:       {summary['success_rate']:.1f}%\n")
            f.write(f"  Successful Logins:  {summary['successful_logins']}\n")
            f.write(f"  Failed Logins:      {summary['failed_logins']}\n")
            f.write(f"  Errors:             {summary['errors']}\n\n")
            
            f.write(f"Performance:\n")
            f.write(f"  Avg Login Time:     {summary['avg_login_time']:.3f}s\n")
            f.write(f"  Median Login Time:  {summary['median_login_time']:.3f}s\n")
            f.write(f"  Min Login Time:     {summary['min_login_time']:.3f}s\n")
            f.write(f"  Max Login Time:     {summary['max_login_time']:.3f}s\n")
            f.write(f"  Total Duration:     {summary['total_duration']:.2f}s\n")
            f.write(f"  Throughput:         {summary['throughput']:.1f} users/sec\n")
        
        # Overall summary
        f.write(f"\n\n{'='*80}\n")
        f.write("OVERALL SUMMARY\n")
        f.write(f"{'='*80}\n\n")
        
        success_rates = [r['summary']['success_rate'] for r in results]
        throughputs = [r['summary']['throughput'] for r in results]
        
        f.write(f"Average Success Rate:  {np.mean(success_rates):.1f}%\n")
        f.write(f"Average Throughput:    {np.mean(throughputs):.1f} users/sec\n")
        f.write(f"Max Throughput:        {max(throughputs):.1f} users/sec\n")
        f.write(f"Max Users Tested:      {max([r['config']['num_users'] for r in results])}\n")
        
    print(f"✓ Report saved to: {output_file}")
    return output_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Visualize stress test results")
    parser.add_argument("--results", type=str, help="Path to results JSON file (default: most recent)")
    parser.add_argument("--output", type=str, default="stress_test", help="Output file prefix")
    
    args = parser.parse_args()
    
    try:
        results, results_file = load_results(args.results)
        
        print(f"\nGenerating visualizations from: {results_file}")
        print(f"Total tests: {len(results)}\n")
        
        # Create charts
        chart_file = create_performance_charts(results, args.output)
        
        # Create report
        report_file = create_summary_report(results, args.output)
        
        print(f"\n{'='*70}")
        print("VISUALIZATION COMPLETE")
        print(f"{'='*70}")
        print(f"Charts: {chart_file}")
        print(f"Report: {report_file}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

