import os
import django
from django.utils import timezone

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from account.models import BotAccount, Proxy, Session
from analytics.models import ActionLog

def populate_test_data():
    print("🚀 Populating test data...")

    # 1. Create a Proxy
    proxy, _ = Proxy.objects.get_or_create(
        host="127.0.0.1",
        port=8080,
        protocol="http",
        defaults={"username": "testuser", "country_code": "US"}
    )
    print(f"✅ Proxy created: {proxy}")

    # 2. Create a Bot Account
    account, _ = BotAccount.objects.get_or_create(
        username="test_bot_01",
        defaults={
            "password_encrypted": "encrypted_dummy_pass",
            "proxy": proxy,
            "status": "active",
            "trust_score": 0.85
        }
    )
    print(f"✅ Bot Account created: {account.username}")

    # 3. Create a Session
    session, _ = Session.objects.get_or_create(
        account=account,
        status="active",
        defaults={"started_at": timezone.now()}
    )
    print(f"✅ Session created: ID {session.id}")

    # 4. Create an Action Log
    action, created = ActionLog.objects.get_or_create(
        account=account,
        session=session,
        action_type="follow",
        target_username="cristiano",
        defaults={
            "success": True,
            "metadata": "Test follow action",
            "target_url": "https://instagram.com/cristiano"
        }
    )
    # 5. Create User Behavior
    from analytics.models import UserBehavior
    behavior, created = UserBehavior.objects.get_or_create(
        account=account,
        behavior_type="scrolling",
        defaults={
            "data": '{"duration": 120, "distance": 5000}',
            "recorded_at": timezone.now()
        }
    )
    if created:
        print(f"✅ User Behavior created: {behavior.behavior_type}")
    
    # 6. Create Daily Analytics
    from analytics.models import DailyAnalytics
    daily, created = DailyAnalytics.objects.get_or_create(
        account=account,
        date=timezone.now().date(),
        defaults={
            "follows_count": 5,
            "likes_count": 20,
            "downloads_count": 2
        }
    )
    if created:
        print(f"✅ Daily Analytics created for today")

    print("\n✨ Done! Now refresh your API or Swagger UI.")

if __name__ == "__main__":
    populate_test_data()
