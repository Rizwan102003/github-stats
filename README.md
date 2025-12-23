# Github Stats

GitHub Stats CLI is a lightweight command-line tool that lets you fetch and analyze pull requests made by any GitHub user, filtered by date range and labels, and neatly grouped by repository.

## Features :

- Fetch PRs for any GitHub username
- Filter by date range (start & end)
- Filter by label (--label wocs)
- Group PRs by repository
- Show creation and merge times
- Pretty terminal output using rich

## Installation
```bash
git clone https://github.com/Rizwan102003/github-stats.git
cd github-stats
```
for windows :
```bash
pip install -r requirements.txt
```

for linux distros :
use python3 instead of python

## Usage
```bash
python github_pr_stats.py --user <github_username> --start <YYYY-MM-DD> --end <YYYY-MM-DD> [--label <label_name>]
```
example 
```bash
python github_pr_stats.py --user Rizwan102003 --start 2025-11-01 --end 2025-12-31 --label wocs
```
