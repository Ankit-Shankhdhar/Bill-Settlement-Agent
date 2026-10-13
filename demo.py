"""Quick smoke test for the Bill Splitter project.

Runs the memory/tools/settlement logic directly (no API key needed),
then optionally runs the live agent if GROQ_API_KEY is set.

For the graded multi-step trace demo, see demo_notebook.ipynb instead --
this script is just a fast sanity check.
"""

import os

from memory import BillMemory
from tools import BillTools


def demo_tools_only():
    print("=" * 60)
    print("PART 1: Testing memory + tools directly (no API needed)")
    print("=" * 60)

    memory = BillMemory()
    tools = BillTools(memory)

    print("\nadd_share(Rahul, 900):")
    print(tools.add_share("Rahul", 900))

    print("\nadd_share(Aman, 600):")
    print(tools.add_share("Aman", 600))

    print("\nadd_share(Priya, -50)  [should fail cleanly]:")
    print(tools.add_share("Priya", -50))

    print("\nsettle_up():")
    print(tools.settle_up())


def demo_live_agent():
    if not os.getenv("GROQ_API_KEY"):
        print("\n" + "=" * 60)
        print("PART 2: Skipped (set GROQ_API_KEY to try the live agent)")
        print("=" * 60)
        return

    from agent import BillSplitterAgent

    print("\n" + "=" * 60)
    print("PART 2: Live agent demo")
    print("=" * 60)

    memory = BillMemory()
    tools = BillTools(memory)
    agent = BillSplitterAgent(tools)

    goals = [
        "Rahul paid 900 for dinner. Aman paid 600 for the same dinner.",
        "Now settle the bill and tell us who owes whom.",
    ]

    for goal in goals:
        print(f"\nYou: {goal}")
        print(f"Agent: {agent.chat(goal, verbose=True)}")


if __name__ == "__main__":
    demo_tools_only()
    demo_live_agent()
