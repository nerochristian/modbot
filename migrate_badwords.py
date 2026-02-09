
import sqlite3
import json

DB_PATH = "modbot.db"

NEW_BADWORDS = [
    "nigger", "nigga", "chink", "spic", "kike",
    "faggot", "fag", "tranny", "dyke",
    "retard", "autist",
    "kys", "kill yourself", "end your life"
]

def migrate():
    print(f"Connecting to {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT guild_id, settings FROM guild_settings")
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} guilds.")
        
        for guild_id, settings_json in rows:
            try:
                settings = json.loads(settings_json)
                
                # Check if badwords exist and are different
                current = settings.get("automod_badwords")
                print(f"Guild {guild_id}: Current badwords count: {len(current) if current else 0}")
                
                # Force update to new list
                settings["automod_badwords"] = NEW_BADWORDS
                
                new_json = json.dumps(settings)
                cursor.execute(
                    "UPDATE guild_settings SET settings = ? WHERE guild_id = ?",
                    (new_json, guild_id)
                )
                print(f"Guild {guild_id}: Updated badwords.")
                
            except json.JSONDecodeError:
                print(f"Guild {guild_id}: Failed to decode settings.")
                
        conn.commit()
        conn.close()
        print("Migration complete.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
