#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

fig = plt.figure(figsize=(16, 10))
fig.suptitle('RHUL Trading Platform Project - Contribution Analysis\nWenbin Wu vs Others', fontsize=14, fontweight='bold')

email_people = ['Wenbin Wu', 'Mariol Jonuzaj', 'Alessio Sancetta', 'Francesco Feri', 'Michael Naef']
email_colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#f39c12']
email_content = [61.5, 22.6, 11.9, 3.1, 1.0]
email_sent = [669, 276, 162, 36, 16]

code_people = ['Wenbin Wu', 'Philipp Chapkovski', 'Mariol Jonuzaj']
code_colors = ['#2ecc71', '#e67e22', '#3498db']
code_lines = [89.5, 8.1, 2.5]
code_commits = [69.6, 19.3, 11.1]

paper_people = ['Wenbin Wu', 'Mariol Jonuzaj', 'Alessio Sancetta']
paper_colors = ['#2ecc71', '#3498db', '#9b59b6']
paper_lines_added = [79.8, 18.7, 1.5]

ax1 = fig.add_subplot(2, 3, 1)
ax1.pie(email_content, labels=[p.split()[0] for p in email_people], autopct='%1.1f%%', colors=email_colors, startangle=90)
ax1.set_title('EMAIL: Content Written\n(Characters)')

ax2 = fig.add_subplot(2, 3, 2)
ax2.pie(code_lines, labels=[p.split()[0] for p in code_people], autopct='%1.1f%%', colors=code_colors, startangle=90)
ax2.set_title('CODE: Lines Added\n(Git History)')

ax3 = fig.add_subplot(2, 3, 3)
ax3.pie(paper_lines_added, labels=[p.split()[0] for p in paper_people], autopct='%1.1f%%', colors=paper_colors, startangle=90)
ax3.set_title('PAPER: Lines Added\n(Git History)')

ax4 = fig.add_subplot(2, 3, 4)
categories = ['Email\nContent', 'Code\nLines', 'Paper\nLines', 'Code\nCommits', 'Email\nThreads']
wenbin_pct = [61.5, 89.5, 79.8, 69.6, 49.8]
x = np.arange(len(categories))
bars = ax4.bar(x, wenbin_pct, color='#2ecc71', edgecolor='black', linewidth=1.2)
ax4.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50% line')
ax4.set_xticks(x)
ax4.set_xticklabels(categories)
ax4.set_ylabel('Wenbin\'s Contribution (%)')
ax4.set_title('Wenbin\'s Share Across All Metrics')
ax4.set_ylim(0, 100)
for bar, pct in zip(bars, wenbin_pct):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{pct}%', ha='center', fontsize=10, fontweight='bold')
ax4.legend()

ax5 = fig.add_subplot(2, 3, 5)
ax5.axis('off')
summary = """
CONTRIBUTION SUMMARY
====================

EMAIL (Feb 2024 - Jan 2026):
  Wenbin:   61.5% content, 50% threads
  Mariol:   22.6%
  Alessio:  11.9%
  Francesco: 3.1%
  Michael:   1.0%

CODE (platform git):
  Wenbin:   89.5% (86k lines)
  Philipp:   8.1% (initial scaffold)
  Mariol:    2.5%
  Others:    0%

PAPER (paper git):
  Wenbin:   79.8% lines added
  Mariol:   18.7%
  Alessio:   1.5%
"""
ax5.text(0.05, 0.95, summary, transform=ax5.transAxes, fontsize=10, 
         verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

ax6 = fig.add_subplot(2, 3, 6)
ax6.axis('off')
key_finding = """
KEY FINDING
===========

Francesco Feri & Michael Naef:
  - 0 code commits, 0 paper commits
  - Email participation only

Alessio Sancetta:
  - 0 code commits
  - 1.5% paper (comments only)
  - 11.9% email content

Wenbin Wu is dominant contributor:
  - 89.5% of platform code
  - 79.8% of paper manuscript
  - 61.5% of email content
  - 49.8% of threads started
"""
ax6.text(0.05, 0.95, key_finding, transform=ax6.transAxes, fontsize=11,
         verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='#ffcccc', alpha=0.7))

plt.tight_layout()
output_path = os.path.join(OUTPUT_DIR, 'contribution_analysis.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"Saved to {output_path}")
