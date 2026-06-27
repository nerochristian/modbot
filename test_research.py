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
        sentiment="neutral",
        intents=["Research this."],
        language="en"
    )
    
    try:
        res = await client.converse(
            message=DummyMessage(),
            user_content="research the latest zenless zone zero upd",
            recent_messages=[],
            signals=signals,
            is_continuation=False,
            image_context=None,
            is_image_question=False,
            location_context="",
            settings=None
        )
        print("Result:", res)
    except Exception as e:
        print("Crash:", e)

    if DummyBot.session:
        await DummyBot.session.close()

asyncio.run(main())
