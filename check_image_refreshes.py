#!/usr/bin/env python3
"""
Check how many images were refreshed in the last 3 days
"""
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.db.models import TgAnalyticsEvent

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:XGlKgqmSQtgFMVsVkGtFjAzYZlAULdwo@trolley.proxy.rlwy.net:18646/railway")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Calculate date range
now = datetime.utcnow()
three_days_ago = now - timedelta(days=3)

print(f"\n🔄 IMAGE REFRESHES - LAST 3 DAYS")
print(f"   From: {three_days_ago.strftime('%Y-%m-%d %H:%M')}")
print(f"   To:   {now.strftime('%Y-%m-%d %H:%M')}")

# Count refresh events
total = session.query(func.count(TgAnalyticsEvent.id)).filter(
    TgAnalyticsEvent.event_name == 'image_refresh',
    TgAnalyticsEvent.created_at >= three_days_ago
).scalar()

print(f"\n📊 Total refreshes: {total}")
print(f"💰 Cost: ${total * 0.0031:.2f}")
print(f"📈 Per day: {total / 3:.1f} refreshes (${total * 0.0031 / 3:.2f}/day)")

session.close()
