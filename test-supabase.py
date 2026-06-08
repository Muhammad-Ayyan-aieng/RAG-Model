from src.config import settings
from supabase import create_client

print(f"URL: {settings.SUPABASE_URL}")
print(f"Key starts with: {settings.SUPABASE_ANON_KEY[:20]}...")

try:
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    print("✅ Connection successful!")
    
    # Try a simple query
    result = client.table("users").select("*").limit(1).execute()
    print(f"✅ Query successful: {result}")
    
except Exception as e:
    print(f"❌ Error: {e}")