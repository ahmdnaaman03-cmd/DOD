#!/bin/bash
cd /home/Ahmdnoaman/dod

# 1. Update .gitignore
cat << 'IGN' >> .gitignore
.env
*.env
backups/
__pycache__/
*.pyc
IGN
git rm --cached .env 2>/dev/null || true

# 2. Setup Auto-Sync Cron Job (pulls code every 1 min)
(crontab -l 2>/dev/null | grep -v "git pull"; echo "* * * * * cd /home/Ahmdnoaman/dod && git pull origin main && touch /var/www/ahmdnoaman_pythonanywhere_com_wsgi.py") | crontab -

echo "SUCCESS: Auto-Sync setup complete!"
