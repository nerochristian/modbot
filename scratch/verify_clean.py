import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from cogs import behavior_profiling as bp  # noqa: E402

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name} {detail}".encode("ascii", "replace").decode("ascii"))


# ---- Case 1: the EXACT reported leak (reasoning + word-count tally, truncated)
LEAKED = """We need to produce output with exact structure:
Behavioral & Personality Profile: [USERNAME]
Then sections with bolding (Text) for section headers and subcategories. Must include empty blank lines between major sections.
We need to output very short, about 250-350 words total.
Let's draft:

**Behavioral & Personality Profile: A$hley**

**General Tone & Communication Style**
**Tone:** Hyper hype, all caps, lots of slang, random emojis, chaotic.
**Style:** Fast-fire, meme-heavy, mixes serious talk with absurd jokes.

**Primary Interests & Topics**
**Gaming:** Talks about strategies, stats, and team bragging.
**Anime & pop culture:** References shows and debates.

**Toxicity & Friendliness Level**
**Toxic:** Frequently uses aggressive language and repeated bans.
**Friendly:** Still engages with the group and shares inside jokes.

**Notable Behavioral Patterns**
**Instigator:** Constantly brings up bans, jails, and purge commands.
**Class clown:** Drops random caps and nonsensical phrases.

**Summary**
A$hley is the chaotic hype-man of the server: he floods chat with caps, memes, and endless banter.

Now count words. Let's count roughly.
Words count:
Behavioral(1) & (2) Personality(3) Profile:(4) A$hley(5)
General(6) Tone(7) & (8) Communication(9) Style(10)
Tone:(11) Hyper(12) hype,(13) all(14) caps,(15) lots(16) of(17) slang,(18) random(19) emojis,(20) chaotic.(21)
Style:(22) Fast-fire,(23) meme-heavy,(24) mixes(25) serious(26"""

c1 = bp._clean_profile_output(LEAKED)
check("leak: non-empty", c1)
check("leak: drops leading 'We need to produce'", "We need to produce" not in c1)
check("leak: drops \"Let's draft\"", "Let's draft" not in c1)
check("leak: drops word tally", "Behavioral(1)" not in c1 and "(22)" not in c1)
check("leak: drops 'Now count words'", "Now count words" not in c1)
check("leak: starts at heading", c1.startswith("**Behavioral & Personality Profile: A$hley**"))
check("leak: keeps all 5 sections", bp._count_profile_sections(c1) == 5,
      f"(got {bp._count_profile_sections(c1)})")
check("leak: keeps blank lines between sections", "\n\n**General Tone" in c1)
check("leak: ends on summary prose", c1.rstrip().endswith("endless banter."))
print("\n--- CLEANED CASE 1 ---")
print(c1.encode("ascii", "replace").decode("ascii"))
print("--- END ---\n")

# ---- Case 2: pure reasoning, no profile => must be rejected (triggers failover)
PURE = """We need to output profile with exact structure, using bold headers.
Must include empty blank lines between major sections. Must be very short 250-350 words.
Let's think about what sections to use.
I'll aim for about 280 words.
Make sure there are empty blank lines between major sections."""
check("pure-reasoning rejected", bp._clean_profile_output(PURE) == "")

# ---- Case 3: <think> tags
THINK = """<think>
Okay the user wants a profile. Let me plan the sections and count words.
</think>
**Behavioral & Personality Profile: Bob**

**General Tone & Communication Style**
**Tone:** Calm.

**Primary Interests & Topics**
**Gaming:** Chess.

**Toxicity & Friendliness Level**
**Friendly:** Polite.

**Notable Behavioral Patterns**
**Lurker:** Rarely posts.

**Summary**
Bob is a quiet lurker who keeps to himself."""
c3 = bp._clean_profile_output(THINK)
check("think-tag stripped", "Okay the user wants" not in c3 and "<think>" not in c3)
check("think-tag profile intact", bp._count_profile_sections(c3) == 5)

# ---- Case 4: unclosed <think> (finish_reason=length)
UNCLOSED = "**Behavioral & Personality Profile: X**\n\n<think>\nlet me reconsider the wording and"
check("unclosed think tail dropped", "let me reconsider" not in bp._clean_profile_output(UNCLOSED))

# ---- Case 5: clean profile passes through untouched
CLEAN = """**Behavioral & Personality Profile: Zoe**

**General Tone & Communication Style**
**Tone:** Warm and direct.
**Style:** Short sentences.

**Primary Interests & Topics**
**Art:** Shares sketches often.
**Music:** Debates album rankings.

**Toxicity & Friendliness Level**
**Friendly:** Welcomes newcomers.
**Roughhousing:** Teases close friends only.

**Notable Behavioral Patterns**
**Encourager:** Hypes other people's work.
**Peacemaker:** Defuses arguments early.

**Summary**
Zoe is the server's steady, encouraging presence."""
c5 = bp._clean_profile_output(CLEAN)
check("clean profile preserved verbatim", c5 == CLEAN.strip(),
      "" if c5 == CLEAN.strip() else "MUTATED")

# ---- Case 6: intro-sentence anchoring (no bold heading)
INTRO = """We must follow the structure. Let's draft.
Here is the behavioral and personality profile for Kim.

**General Tone & Communication Style**
**Tone:** Blunt.

**Primary Interests & Topics**
**Sports:** Football talk.

**Toxicity & Friendliness Level**
**Friendly:** Mostly kind.

**Summary**
Kim is blunt but well-meaning."""
c6 = bp._clean_profile_output(INTRO)
check("intro anchor drops preamble", "We must follow" not in c6 and c6.startswith("Here is the behavioral"))

# ---- Case 7: mention defanging still works
check("@everyone defanged", "@\u200beveryone" in bp._clean_profile_output(CLEAN.replace("Zoe is the server's", "@everyone Zoe is the server's")))

# ---- Case 8: non-string
check("non-string -> empty", bp._clean_profile_output(None) == "")

# ---- Case 9: multiple drafts -> last complete one wins
MULTI = CLEAN.replace("Zoe", "Draft1") + "\n\nActually let me redo that.\n\n" + CLEAN
c9 = bp._clean_profile_output(MULTI)
check("last draft wins", "Draft1" not in c9 and "Zoe" in c9)

print()
failed = [n for n, ok, _ in results if not ok]
print(f"{len(results) - len(failed)}/{len(results)} passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
