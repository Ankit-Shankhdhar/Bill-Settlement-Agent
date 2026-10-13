from settlement import calculate_settlement


class BillTools:

    def __init__(self, memory):
        self.memory = memory

    # ============================== #
    #            TOOL 1              #
    # ============================== #

    def add_share(self, person, amount):
        """Record a payment made by a person toward the shared bill."""

        person = str(person).strip()

        if not person:
            return {
                "success": False,
                "error": "Person's name cannot be empty.",
            }

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": f"'{amount}' is not a valid number.",
            }

        if amount <= 0:
            return {
                "success": False,
                "error": "Amount must be greater than zero.",
            }

        self.memory.add_expense(person, amount)

        return {
            "success": True,
            "message": f"{person} paid \u20b9{amount:.2f}",
            "expenses": self.memory.get_expenses(),
        }

    # ============================== #
    #            TOOL 2              #
    # ============================== #

    def settle_up(self):
        """Calculate fair shares, balances, and the simplest repayments."""

        if not self.memory.has_expenses():
            return {
                "success": False,
                "error": "No payments have been recorded yet.",
            }

        return {
            "success": True,
            **calculate_settlement(self.memory.get_expenses()),
        }


# ============================== #
#     GROQ TOOL DEFINITIONS      #
# ============================== #

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_share",
            "description": (
                "Record a payment made by a person toward a shared "
                "expense. Use this when the user tells you that "
                "someone paid a specific amount. Do not use it to "
                "calculate settlements."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "person": {
                        "type": "string",
                        "description": "Name of the person who paid.",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount that the person paid.",
                    },
                },
                "required": ["person", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "settle_up",
            "description": (
                "Calculate everyone's fair share, net balances, and "
                "the simplest set of repayments. Use this when the "
                "user asks who owes whom or wants to settle the bill."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]
