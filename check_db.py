import os
import django
import sys

# Setup django
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from account.models import BotAccount

accounts = BotAccount.objects.all()
print(f"Total accounts: {accounts.count()}")
for acc in accounts:
    print(f"ID: {acc.id}, Username: {acc.username}, Status: {acc.status}")
