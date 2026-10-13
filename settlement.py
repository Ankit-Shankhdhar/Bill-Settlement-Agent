"""Settlement math for the Bill Splitter agent.

`calculate_balances` does the shared work (totals, fair share, net
balance per person). `calculate_settlement` builds on it to also
produce the simplest set of repayments.
"""


def calculate_balances(expenses):
    """Return totals, fair share, and each person's net balance.

    Positive balance -> person is owed money.
    Negative balance -> person owes money.
    """

    if not expenses:
        return {
            "total": 0.0,
            "fair_share": 0.0,
            "people": {},
            "balances": {},
        }

    # 1. How much each person paid in total.
    paid = {}

    for expense in expenses:
        person = expense["person"]
        amount = float(expense["amount"])
        paid[person] = paid.get(person, 0.0) + amount

    # 2. Everyone's equal share.
    total = sum(paid.values())
    number_of_people = len(paid)
    fair_share = total / number_of_people

    # 3. Net balance per person.
    balances = {
        person: round(amount_paid - fair_share, 2)
        for person, amount_paid in paid.items()
    }

    return {
        "total": round(total, 2),
        "fair_share": round(fair_share, 2),
        "people": paid,
        "balances": balances,
    }


def calculate_settlement(expenses):
    """Return balances plus the simplest set of repayments."""

    summary = calculate_balances(expenses)

    if not summary["balances"]:
        return {**summary, "settlements": []}

    creditors = []
    debtors = []

    for person, balance in summary["balances"].items():
        if balance > 0:
            creditors.append({"person": person, "amount": balance})
        elif balance < 0:
            debtors.append({"person": person, "amount": abs(balance)})

    # Greedily match the biggest debts to the biggest credits.
    settlements = []
    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]

        amount = round(min(debtor["amount"], creditor["amount"]), 2)

        settlements.append({
            "from": debtor["person"],
            "to": creditor["person"],
            "amount": amount,
        })

        debtor["amount"] = round(debtor["amount"] - amount, 2)
        creditor["amount"] = round(creditor["amount"] - amount, 2)

        if debtor["amount"] == 0:
            i += 1

        if creditor["amount"] == 0:
            j += 1

    return {**summary, "settlements": settlements}
