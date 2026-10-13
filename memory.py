class BillMemory:
    """Stores every recorded payment for the current bill."""

    def __init__(self):
        self.expenses = []

    def add_expense(self, person, amount):
        self.expenses.append({
            "person": person,
            "amount": float(amount)
        })

    def get_expenses(self):
        return self.expenses

    def has_expenses(self):
        return len(self.expenses) > 0

    def clear(self):
        self.expenses = []

    def total(self):
        return sum(expense["amount"] for expense in self.expenses)
