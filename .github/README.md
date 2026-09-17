# GitHub Configuration

This directory contains GitHub repository configuration files.

## Automatic Branch Deletion

The `settings.yml` file configures automatic branch deletion after pull request merging.

### Setup Options

You have **two options** to enable automatic branch deletion:

#### Option 1: Manual Configuration (Recommended)

1. Go to your GitHub repository
2. Navigate to **Settings** > **General**
3. Scroll to **Pull Requests** section
4. Check ✅ **Automatically delete head branches**

This is the simplest approach and takes effect immediately.

#### Option 2: Probot Settings App

1. Install the [Probot Settings app](https://github.com/apps/settings) on your repository
2. The app will automatically apply settings from `.github/settings.yml`
3. Any changes to `settings.yml` will be synced to GitHub

### Current Configuration

The `settings.yml` file includes:

- ✅ `delete_branch_on_merge: true` - Auto-delete branches after PR merge
- ✅ Branch protection rules for `main`
- ✅ Automated security fixes enabled
- ✅ Vulnerability alerts enabled

### Note

The `settings.yml` file serves as:
- **Documentation** of desired repository settings
- **Configuration source** if using Probot Settings app
- **Reference** for manual configuration

Without the Probot app, you must configure these settings manually in GitHub's UI.
