# AgentMail Integration for Henry (Clawdbot)

## Overview

AgentMail is an API-first email platform for AI agents. This integration will give Henry his own email address for:
- Receiving notifications from services
- Sending reports/summaries to Matt
- Email-based workflows with clients
- Agent identity for external services

## Status: NOT YET IMPLEMENTED

Waiting on: AgentMail API key from console.agentmail.to

## Setup Steps

### 1. Create AgentMail Account
- [ ] Go to [console.agentmail.to](https://console.agentmail.to)
- [ ] Create account
- [ ] Generate API key from dashboard

### 2. Configure Clawdbot
- [ ] Add `AGENTMAIL_API_KEY=<key>` to `~/clawd/.env`
- [ ] Add `AGENTMAIL_INBOX=henry@agentmail.to` to `~/clawd/.env`

### 3. Create Inbox
```bash
python ~/clawd/skills/agentmail/scripts/create_inbox.py \
  --username henry \
  --display-name "Henry (CMT Assistant)"
```

### 4. Test Send/Receive
```bash
# Send test email
python ~/clawd/skills/agentmail/scripts/send_email.py \
  --to "matt@clearmatchtalent.com" \
  --subject "Test from Henry" \
  --text "AgentMail integration is working!"

# Check inbox
python ~/clawd/skills/agentmail/scripts/check_inbox.py
```

### 5. Set Up Webhook (Optional)
For real-time email processing, configure webhook with sender allowlist to prevent prompt injection.

## Files Created

```
~/clawd/skills/agentmail/
├── SKILL.md                    # Skill documentation
└── scripts/
    ├── send_email.py           # Send emails
    ├── check_inbox.py          # Check inbox for messages
    ├── list_inboxes.py         # List all inboxes
    └── create_inbox.py         # Create new inbox
```

## Security Considerations

⚠️ **Webhook Allowlist Required**: Incoming emails can contain prompt injection attacks. Before enabling webhooks, implement sender allowlist in Clawdbot config.

## Use Cases

1. **Daily Digest**: Henry sends morning summary of tasks/calendar
2. **Alert Forwarding**: Forward important notifications to Matt
3. **Client Communication**: Automated follow-ups on recruiting workflows
4. **Service Notifications**: Receive alerts from external services

## Cost

AgentMail uses usage-based pricing. Estimated cost for typical agent use: ~$5-10/month.

## References

- [AgentMail Console](https://console.agentmail.to)
- [AgentMail Docs](https://docs.agentmail.to)
- Clawdbot skill: `~/clawd/skills/agentmail/SKILL.md`
