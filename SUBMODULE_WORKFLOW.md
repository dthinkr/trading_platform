# Git Submodule Workflow for platform-paper

The `platform-paper` directory is now configured as a **git submodule**. This means it's a separate repository tracked within the main `trading_platform` repository.

## ✅ What This Means

- Changes in `platform-paper/` are committed to its own repository: `https://github.com/dthinkr/trading-platform-paper.git`
- The main `trading_platform` repo tracks which specific commit of `platform-paper` it's using
- Both repositories stay in sync, but changes flow through the submodule first

## 📝 Daily Workflow

### Making Changes in platform-paper

```bash
# 1. Navigate to the submodule
cd platform-paper/

# 2. Make your changes (edit .tex files, add figures, etc.)

# 3. Commit and push to the platform-paper repo
git add .
git commit -m "Update paper content"
git push origin main

# 4. Go back to the main repo
cd ..

# 5. Update the main repo to track the new commit
git add platform-paper
git commit -m "Update platform-paper submodule"
git push
```

### Pulling Latest Changes

```bash
# In the main trading_platform directory
git pull

# Update all submodules to their tracked commits
git submodule update --init --recursive
```

Or, to pull and update submodules in one command:
```bash
git pull --recurse-submodules
```

### When Cloning the Repository (For Others)

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/dthinkr/trading_platform

# OR, if already cloned without submodules
git submodule update --init --recursive
```

## 🔍 Checking Status

```bash
# See submodule status
git submodule status

# See if submodule has uncommitted changes
cd platform-paper/
git status
```

## 🚨 Important Notes

1. **Always commit changes in the submodule first**, then update the main repo
2. The main repo only stores a **reference** to a specific commit in platform-paper
3. If you edit files in `platform-paper/`, you need to commit in TWO places:
   - First in `platform-paper/` (the submodule repo)
   - Then in the root (to update the commit reference)

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Check submodule status | `git submodule status` |
| Update submodule to latest | `cd platform-paper && git pull origin main && cd .. && git add platform-paper && git commit -m "Update submodule"` |
| Clone with submodules | `git clone --recurse-submodules <repo-url>` |
| Initialize submodules after clone | `git submodule update --init --recursive` |

## ✨ Benefits

- ✅ Changes in platform-paper are automatically synced to its own repo
- ✅ The main repo always knows exactly which version of the paper it's using
- ✅ Multiple people can work on the paper independently
- ✅ Easy to roll back to previous versions of the paper
- ✅ The paper can be developed and versioned separately from the platform

---

**Current Setup:**
- Submodule: `platform-paper/`
- Remote: `https://github.com/dthinkr/trading-platform-paper.git`
- Branch: `main`

