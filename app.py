import os
from bot import bot, dp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

scheduler = AsyncIOScheduler()

async def main():
    # Hugging Face Spaces требует webhook режим
    webhook_url = os.getenv("SPACE_HOST", "")
    if webhook_url:
        webhook_path = f"{webhook_url.rstrip('/')}/webhook"
        await bot.set_webhook(webhook_path)
        print(f"Webhook set to: {webhook_path}")
    
    if not scheduler.running:
        scheduler.start()
    
    print("Bot started successfully!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
