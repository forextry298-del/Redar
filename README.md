# HDAR full registration prototype

This is a separate Flask app inspired by the visible registration/login flow at the reference URL. It does not reproduce the reference site's private backend or verify its actual business features.

## Included
- Registration page at `/registration` and `/register`
- Login with username or mobile number
- Country selection, name, username, mobile number and password
- Referral URL format `/registration?ref=REFERRALCODE`
- Unique referral codes and direct-referral attribution
- Dashboard with shareable invite link, direct referrals, demo balance and ledger
- UGX 3,000 welcome credit for local UI testing
- Responsive layout and community links

## Run locally in Termux or PC
```bash
python -m venv .venv
# Linux/macOS/Termux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000.

## Deploy separately on Render
Create a new GitHub repository called `HDAR`, upload these files, then create a new Render Web Service from that repository. Set `SECRET_KEY` to a strong random value. For persistent users, configure a persistent disk mounted at `/var/data` and set `DATABASE_PATH=/var/data/hdar.db`. SQLite on an ephemeral filesystem can lose data after restart or redeploy.

## Important scope and money handling
The UGX 3,000 welcome credit is a prototype/demo balance for testing; it is not real cash and cannot be withdrawn in this starter. No deposit collection, mobile-money transfer, investment plan, return guarantee, withdrawal payout, or referral commission payment is implemented. Add those only after specifying and testing legitimate payment and accounting requirements.
