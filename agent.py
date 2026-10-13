import os
import json

from groq import Groq
from dotenv import load_dotenv

from tools import TOOLS

load_dotenv()

SYSTEM_PROMPT = """
You are an intelligent Bill Splitter Agent.

Your job is to help users split shared expenses and determine
who owes whom.

You have exactly two tools:

1. add_share(person, amount)
2. settle_up()

IMPORTANT RULES:

- Remember information throughout the conversation.
- When someone pays money toward a shared expense, use add_share().
- Do not invent payments.
- Do not manually calculate balances or settlements yourself.
- Use settle_up() when the user asks who owes whom, asks to settle,
  or requests the final repayment plan.
- Always use the tool result for financial calculations.
- If a tool returns an error, explain it to the user instead of
  guessing or retrying blindly.
- Explain results clearly.
- Currency is INR unless the user specifies otherwise.
- Be concise but helpful.
- Never claim that someone paid money unless it was provided by the
  user.
"""


class BillSplitterAgent:

    def __init__(self, bill_tools, model="openai/gpt-oss-20b", max_steps=8):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Create a .env file "
                "(see .env.example) with your Groq API key."
            )

        self.client = Groq(api_key=api_key)
        self.bill_tools = bill_tools
        self.model = model
        self.max_steps = max_steps

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def execute_tool(self, tool_call):
        tool_name = tool_call.function.name

        try:
            arguments = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": f"Could not parse arguments for '{tool_name}'.",
            }

        try:
            if tool_name == "add_share":
                return self.bill_tools.add_share(
                    arguments.get("person"),
                    arguments.get("amount"),
                )

            if tool_name == "settle_up":
                return self.bill_tools.settle_up()

            return {
                "success": False,
                "error": f"Unknown tool '{tool_name}'.",
            }

        except Exception as exc:  # noqa: BLE001 - surface any tool failure to the model
            return {
                "success": False,
                "error": f"Tool '{tool_name}' failed: {exc}",
            }

    def chat(self, user_message, verbose=False):
        """Send one user message through the agent loop.

        Set verbose=True to print each step's tool call and result --
        this is what the demo notebook uses to show the multi-step
        trace.
        """

        self.messages.append({
            "role": "user",
            "content": user_message,
        })

        for step in range(1, self.max_steps + 1):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            # Store a plain dict, not the SDK object, so the message
            # history stays consistent and serializable on every turn.
            self.messages.append(
                assistant_message.model_dump(exclude_none=True)
            )

            # No tool call -> the model is done.
            if not assistant_message.tool_calls:
                if verbose:
                    print(f"[step {step}] final answer")
                return assistant_message.content or ""

            # Tool call(s) -> execute each and feed results back.
            for tool_call in assistant_message.tool_calls:
                args = json.loads(tool_call.function.arguments or "{}")
                result = self.execute_tool(tool_call)

                if verbose:
                    print(
                        f"[step {step}] "
                        f"{tool_call.function.name}({args}) -> {result}"
                    )

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        return (
            f"Stopped after {self.max_steps} steps without reaching "
            "a final answer. Try rephrasing your request."
        )
