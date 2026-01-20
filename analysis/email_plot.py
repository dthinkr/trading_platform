#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

plt.style.use('seaborn-v0_8-whitegrid')
fig = plt.figure(figsize=(18, 16))
fig.suptitle('RHUL Trading Platform Project - Contribution Analysis\n(Email & Git History, Aug 2023 - Jan 2026)', fontsize=14, fontweight='bold')

people = ['Wenbin Wu', 'Mariol Jonuzaj', 'Alessio Sancetta', 'Francesco Feri', 'Michael Naef']
colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#f39c12']

sent = [669, 276, 162, 36, 16]
received = [646, 411, 357, 51, 63]
cc = [210, 156, 161, 41, 42]
total_chars_k = [13026.9, 4784.9, 2520.9, 650.6, 212.4]
avg_len = [19472, 17336, 15561, 18073, 13274]
threads_started = [158, 79, 56, 14, 10]

email_months = ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan']
monthly_data = {
    'Wenbin Wu': {'chars': [29.2, 108.9, 37.6, 15.7, 133.1, 1.6, 23.5, 103.9, 96.8, 170.3, 74.7, 81.9], 'count': [14, 29, 16, 6, 45, 3, 13, 30, 57, 51, 31, 23]},
    'Mariol Jonuzaj': {'chars': [66.3, 133.3, 41.7, 18.6, 44.6, 4.6, 19.1, 92.1, 78.4, 85.8, 119.2, 60.5], 'count': [28, 24, 14, 8, 20, 4, 9, 25, 36, 25, 28, 14]},
    'Alessio Sancetta': {'chars': [2.9, 11.1, 1.6, 3.2, 60.4, 2.8, 13.6, 18.7, 28.7, 26.8, 30.5, 46.0], 'count': [2, 7, 3, 1, 21, 3, 5, 12, 19, 14, 9, 11]},
    'Francesco Feri': {'chars': [8.0, 1.5, 0.7, 9.5, 3.2, 1.1, 16.7, 42.9, 23.5, 17.3, 49.8, 18.4], 'count': [3, 1, 1, 5, 2, 1, 6, 6, 8, 6, 11, 2]},
    'Michael Naef': {'chars': [4.5, 0.0, 0.0, 0.0, 0.0, 13.2, 0.2, 10.9, 10.2, 14.1, 1.5, 9.5], 'count': [3, 0, 0, 0, 0, 1, 1, 7, 6, 4, 2, 4]},
}

git_people = ['Wenbin Wu', 'Philipp Chapkovski', 'Mariol Jonuzaj']
git_colors = ['#2ecc71', '#e67e22', '#3498db']
git_commits = [495, 137, 79]
git_lines = [675736, 8993, 4731]
git_months = ['Aug23', 'Sep23', 'Nov23', 'Dec23', 'Jan24', 'Feb24', 'Mar24', 'Apr24', 'May24', 'Jun24', 'Jul24', 'Aug24', 'Sep24', 'Oct24', 'Nov24', 'Dec24', 'Jan25', 'Feb25', 'Mar25', 'Apr25', 'May25', 'Jun25', 'Aug25', 'Sep25', 'Oct25', 'Nov25', 'Dec25', 'Jan26']
git_monthly_commits = {
    'Wenbin Wu': [0, 0, 0, 0, 0, 3, 10, 9, 17, 10, 68, 28, 48, 65, 58, 2, 12, 11, 20, 4, 8, 45, 11, 8, 14, 13, 22, 9],
    'Philipp Chapkovski': [13, 36, 14, 2, 3, 20, 36, 12, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'Mariol Jonuzaj': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 16, 11, 9, 10, 0, 1, 11, 3, 4, 0, 3, 6, 4, 0, 0],
}

ax1 = fig.add_subplot(3, 3, 1)
x = np.arange(len(people))
width = 0.25
ax1.bar(x - width, sent, width, label='Sent', color='#2ecc71')
ax1.bar(x, received, width, label='Received', color='#3498db')
ax1.bar(x + width, cc, width, label='CC\'d', color='#95a5a6')
ax1.set_ylabel('Email Count')
ax1.set_title('Email Volume by Person')
ax1.set_xticks(x)
ax1.set_xticklabels([p.split()[0] for p in people], rotation=45, ha='right')
ax1.legend(loc='upper right', fontsize=8)

ax2 = fig.add_subplot(3, 3, 2)
ax2.pie(total_chars_k, labels=[p.split()[0] for p in people], autopct='%1.1f%%', colors=colors, startangle=90)
ax2.set_title('Email Content Written')

ax3 = fig.add_subplot(3, 3, 3)
ax3.pie(git_commits, labels=[p.split()[0] for p in git_people], autopct='%1.1f%%', colors=git_colors, startangle=90)
ax3.set_title('Git Commits (Total)')

ax4 = fig.add_subplot(3, 3, 4)
x = np.arange(len(email_months))
for i, person in enumerate(people):
    ax4.plot(x, monthly_data[person]['chars'], 'o-', label=person.split()[0], color=colors[i], linewidth=2, markersize=4)
ax4.set_xticks(x)
ax4.set_xticklabels(email_months)
ax4.set_xlabel('Month (2025-2026)')
ax4.set_ylabel('Characters (k)')
ax4.set_title('Monthly Email Content')
ax4.legend(loc='upper left', fontsize=7)

ax5 = fig.add_subplot(3, 3, 5)
x = np.arange(len(email_months))
for i, person in enumerate(people):
    ax5.plot(x, monthly_data[person]['count'], 's-', label=person.split()[0], color=colors[i], linewidth=2, markersize=4)
ax5.set_xticks(x)
ax5.set_xticklabels(email_months)
ax5.set_xlabel('Month (2025-2026)')
ax5.set_ylabel('Email Count')
ax5.set_title('Monthly Email Count')
ax5.legend(loc='upper left', fontsize=7)

ax6 = fig.add_subplot(3, 3, 6)
x = np.arange(len(git_months))
for i, person in enumerate(git_people):
    ax6.plot(x, git_monthly_commits[person], 'o-', label=person.split()[0], color=git_colors[i], linewidth=2, markersize=3)
ax6.set_xticks(x[::3])
ax6.set_xticklabels([git_months[i] for i in range(0, len(git_months), 3)], rotation=45, ha='right')
ax6.set_xlabel('Month')
ax6.set_ylabel('Commits')
ax6.set_title('Monthly Git Commits')
ax6.legend(loc='upper right', fontsize=7)

ax7 = fig.add_subplot(3, 3, 7)
x = np.arange(len(git_people))
ax7.bar(x, git_commits, color=git_colors)
ax7.set_xticks(x)
ax7.set_xticklabels([p.split()[0] for p in git_people])
ax7.set_ylabel('Commits')
ax7.set_title('Total Git Commits')
for i, v in enumerate(git_commits):
    ax7.text(i, v + 10, str(v), ha='center', fontsize=10)

ax8 = fig.add_subplot(3, 3, 8)
x = np.arange(len(git_people))
ax8.bar(x, [l/1000 for l in git_lines], color=git_colors)
ax8.set_xticks(x)
ax8.set_xticklabels([p.split()[0] for p in git_people])
ax8.set_ylabel('Lines Added (k)')
ax8.set_title('Total Lines Added')
for i, v in enumerate(git_lines):
    ax8.text(i, v/1000 + 20, f'{v/1000:.0f}k', ha='center', fontsize=10)

ax9 = fig.add_subplot(3, 3, 9)
ax9.axis('off')
summary = """KEY FINDINGS:

EMAIL (Project Discussion):
• Wenbin: 62% of content, 50% threads started
• Alessio, Francesco, Michael participate
  in emails but 0 code commits

GIT (Code Contribution):
• Wenbin: 495 commits (70%), 676k lines
• Philipp: 137 commits (19%), 9k lines
  (initial scaffold, Aug-May 2024)
• Mariol: 79 commits (11%), 5k lines

Note: Alessio, Francesco, Michael
have ZERO git commits to this codebase."""
ax9.text(0.1, 0.9, summary, transform=ax9.transAxes, fontsize=10, verticalalignment='top', fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
output_path = os.path.join(OUTPUT_DIR, 'email_analysis_plot.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"Saved to {output_path}")
