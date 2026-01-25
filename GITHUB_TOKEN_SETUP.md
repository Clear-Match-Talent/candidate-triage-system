# GitHub Personal Access Token Setup

## Quick Steps

1. **Go to:** https://github.com/settings/tokens/new
2. **Token name:** `candidate-triage-system` (or any name you prefer)
3. **Expiration:** 
   - Choose **"No expiration"** for long-term use, OR
   - Choose **90 days** if you prefer tokens to expire periodically
4. **Select scopes:** Check the box for **`repo`** (this gives full control of private repositories)
5. **Click:** "Generate token"
6. **IMPORTANT:** Copy the token immediately - you won't see it again!

## What the `repo` Scope Does

The `repo` scope provides:
- ✅ Full control of private repositories
- ✅ Read/write access to code
- ✅ Create/delete repositories  
- ✅ Push/pull code
- ✅ Manage repository settings
- ✅ Access private repositories

This is exactly what you need to push your code to GitHub.

## After Creating the Token

Once you have the token, you can:

**Option 1: Use the provided script**
```powershell
cd C:\Users\mdsin\candidate-triage-system
.\push-to-github.ps1 -Token "YOUR_TOKEN_HERE"
```

**Option 2: Push manually**
```powershell
cd C:\Users\mdsin\candidate-triage-system
git remote set-url origin https://YOUR_TOKEN@github.com/mattds34/candidate-triage-system.git
git push -u origin main
```

**Option 3: Let Git prompt you**
```powershell
cd C:\Users\mdsin\candidate-triage-system
git push -u origin main
# When prompted:
# Username: mattds34
# Password: paste your token (not your GitHub password)
```

## Security Note

- Never commit tokens to your repository
- The token is already in `.gitignore` to prevent accidental commits
- If a token is ever exposed, revoke it immediately at https://github.com/settings/tokens
