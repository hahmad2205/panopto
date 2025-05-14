from decouple import config
from supabase import Client, create_client


url = config("SUPABASE_URL")
key = config("SUPABASE_KEY")

supabase_client: Client = create_client(url, key)
