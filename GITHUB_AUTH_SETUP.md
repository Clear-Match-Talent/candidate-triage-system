# GitHub Authentication Setup

The auto-commit workflow requires GitHub authentication on this EC2 instance.

## Quick Setup (Recommended: SSH Key)

### 1. Generate SSH Key
```bash
ssh-keygen -t ed25519 -C "clawdbot-ec2@clearmatchtalent.com" -f ~/.ssh/id_ed25519_github
# Press Enter for no passphrase (this is a server)
```

### 2. Add Public Key to GitHub
```bash
cat ~/.ssh/id_ed25519_github.pub
```

Copy the output, then:
1. Go to https://github.com/settings/keys
2. Click "New SSH key"
3. Paste the public key
4. Title: "EC2 Clawdbot Server"

### 3. Update Git Remote to Use SSH
```bash
cd ~/clawd/candidate-triage-system
git remote set-url origin git@github.com:Clear-Match-Talent/candidate-triage-system.git
```

### 4. Configure SSH
```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
EOF

chmod 600 ~/.ssh/config
```

### 5. Test Connection
```bash
ssh -T git@github.com
# Should say: "Hi Clear-Match-Talent! You've successfully authenticated..."
```

### 6. Test Push
```bash
cd ~/clawd/candidate-triage-system
git push
```

---

## Alternative: Personal Access Token (PAT)

If you prefer HTTPS with a token:

### 1. Create PAT on GitHub
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Scopes: `repo` (full control)
4. Copy the token

### 2. Configure Git Credential Helper
```bash
git config --global credential.helper store
```

### 3. Push (will prompt for credentials once)
```bash
cd ~/clawd/candidate-triage-system
git push
# Username: <your-github-username>
# Password: <paste-your-PAT>
```

Credentials will be saved to `~/.git-credentials` for future use.

---

## Current Status

❌ **Not yet configured** - git push fails with authentication error

Once configured, `commit-status.sh` and `ralph.sh` will auto-commit task completions.
