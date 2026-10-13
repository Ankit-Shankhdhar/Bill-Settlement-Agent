from memory import BillMemory
from tools import BillTools
from agent import BillSplitterAgent


def main():
    print("=" * 50)
    print("       \U0001F4B0 BILL SPLITTER AI AGENT")
    print("=" * 50)
    print("\nType 'exit' to quit.")
    print("Example: Rahul paid 900 for dinner.")
    print("Example: Settle everything.")
    print("=" * 50)

    memory = BillMemory()
    tools = BillTools(memory)

    try:
        agent = BillSplitterAgent(tools)
    except RuntimeError as exc:
        print(f"\n\u274C {exc}")
        return

    while True:
        try:
            user_input = input("\nYou: ")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break

        stripped = user_input.strip()

        if stripped.lower() in ("exit", "quit"):
            print("\nGoodbye! \U0001F44B")
            break

        if not stripped:
            continue

        try:
            answer = agent.chat(user_input)
            print("\n\U0001F916 Agent:", answer)
        except Exception as exc:  # noqa: BLE001 - keep the REPL alive on any failure
            print("\n\u274C Error:", str(exc))


if __name__ == "__main__":
    main()
