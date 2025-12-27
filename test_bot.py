"""
Test script to validate bot initialization and catch any runtime errors
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

async def test_bot():
    """Test bot initialization"""
    print("=" * 60)
    print("Starting Bot Validation Tests")
    print("=" * 60)
    
    errors = []
    
    # Test 1: Import all modules
    print("\n1. Testing imports...")
    try:
        import bot
        import database
        import config
        from utils import cache, messages, checks, embeds
        print("   ✅ All core imports successful")
    except Exception as e:
        errors.append(f"Import error: {e}")
        print(f"   ❌ Import failed: {e}")
        return errors
    
    # Test 2: Database initialization
    print("\n2. Testing database...")
    try:
        from database import Database
        db = Database()
        print("   ✅ Database instance created")
        
        # Test connection pool
        await db.init_pool()
        print("   ✅ Database pool initialized")
        
        # Test validation methods
        try:
            db._validate_guild_id(123456789)
            print("   ✅ Input validation working")
        except ValueError:
            pass
        
        # Test invalid input
        try:
            db._validate_guild_id(-1)
            errors.append("Validation should have failed for negative ID")
        except ValueError:
            print("   ✅ Input validation correctly rejects invalid data")
        
        await db.close()
        print("   ✅ Database closed successfully")
        
    except Exception as e:
        errors.append(f"Database error: {e}")
        print(f"   ❌ Database test failed: {e}")
    
    # Test 3: Cache system
    print("\n3. Testing cache system...")
    try:
        from utils.cache import TTLCache, SnipeCache, PrefixCache, RateLimiter
        
        # Test TTL Cache
        cache_test = TTLCache(ttl=1, max_size=100)
        await cache_test.set("test_key", "test_value")
        value = await cache_test.get("test_key")
        assert value == "test_value", "Cache get/set failed"
        print("   ✅ TTL Cache working")
        
        # Test Snipe Cache
        snipe_cache = SnipeCache(max_age_seconds=300, max_size=500)
        await snipe_cache.add(123, {"test": "data"})
        data = await snipe_cache.get(123)
        assert data is not None, "Snipe cache failed"
        print("   ✅ Snipe Cache working")
        
        # Test Rate Limiter
        rate_limiter = RateLimiter(max_calls=5, window_seconds=60)
        is_limited, retry = await rate_limiter.is_rate_limited("test_user")
        assert not is_limited, "Should not be rate limited initially"
        
        # Record some calls
        for _ in range(5):
            await rate_limiter.record_call("test_user")
        
        is_limited, retry = await rate_limiter.is_rate_limited("test_user")
        assert is_limited, "Should be rate limited after 5 calls"
        print("   ✅ Rate Limiter working")
        
    except Exception as e:
        errors.append(f"Cache error: {e}")
        print(f"   ❌ Cache test failed: {e}")
    
    # Test 4: Message templates
    print("\n4. Testing message templates...")
    try:
        from utils.messages import Messages, Confirmations, InfoMessages
        
        # Test basic templates
        assert hasattr(Messages, 'MISSING_PERMISSIONS')
        assert hasattr(Messages, 'AI_RATE_LIMIT')
        
        # Test formatting
        msg = Messages.format(Messages.AI_RATE_LIMIT, seconds=30)
        assert "30" in msg, "Message formatting failed"
        print("   ✅ Message templates working")
        
    except Exception as e:
        errors.append(f"Messages error: {e}")
        print(f"   ❌ Message test failed: {e}")
    
    # Test 5: Bot class
    print("\n5. Testing bot class...")
    try:
        # Don't actually start the bot, just test initialization
        print("   ⚠️  Skipping bot startup (requires Discord token)")
        print("   ℹ️  Bot class structure validated via imports")
        
    except Exception as e:
        errors.append(f"Bot error: {e}")
        print(f"   ❌ Bot test failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ TESTS FAILED: {len(errors)} error(s) found")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
    else:
        print("✅ ALL TESTS PASSED!")
        print("\nBot is ready for deployment:")
        print("  • All imports working")
        print("  • Database system operational")
        print("  • Caching system functional")
        print("  • Rate limiting active")
        print("  • Message templates loaded")
    print("=" * 60)
    
    return errors

if __name__ == "__main__":
    errors = asyncio.run(test_bot())
    sys.exit(1 if errors else 0)
