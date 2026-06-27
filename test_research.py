import asyncio
import sys

sys.path.append("/root/modbot")

from cogs.aimoderation import GeminiClient, AIConfig, ConversationSignals, ConversationMode

async def main():
    class DummyUser:
        id = 123
        name = "test"
        display_name = "test"

    class DummyGuild:
        name = "test"
        member_count = 1

    class DummyMessage:
        author = DummyUser()
        guild = DummyGuild()
        content = "research the latest zenless zone zero upd"

    class DummyBot:
        user = DummyUser()
        session = None

    class MockCog:
        pass

    config = AIConfig()
    client = GeminiClient(DummyBot(), config)
    
    signals = ConversationSignals(
        mode=ConversationMode.RESEARCH,
        confidence=1.0,
        show_research_indicator=True,
        asks_for_current_info=True,
        asks_for_sources=True,
        asks_for_long_answer=True,
        mentions_moderation=False
    )
    
    try:
        res = await client.converse(
            user_content="research the latest zenless zone zero upd",
            guild=DummyGuild(),
            author=DummyUser(),
            recent_messages=[],
            signals=signals,
            location_context=""
        )
        print("Result:", res)
    except Exception as e:
        print("Crash:", e)

    if DummyBot.session:
        await DummyBot.session.close()

asyncio.run(main())
