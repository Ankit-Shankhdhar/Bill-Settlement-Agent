# Bill Splitter Agent

An LLM agent (via Groq) that tracks shared expenses across a conversation and
figures out the simplest way for everyone to settle up.

## Tools

The agent has exactly two tools. **`add_share(person, amount)`** records that
a person paid a given amount toward a shared expense — the model calls this
whenever the user reports a payment. **`settle_up()`** takes everything
recorded so far, computes each person's fair share of the total, works out
who is owed money and who owes money, and returns the smallest possible set
of person-to-person repayments (a greedy debtor-to-creditor match, not a
naive "everyone pays everyone" list). The model calls `add_share` as
payments come in and calls `settle_up` only when asked who owes whom — it
never does this arithmetic itself.

## Memory

Two layers of memory keep the agent from being a stateless chatbot. `BillMemory`
holds the actual financial state — a running list of `{person, amount}`
payments — and survives for as long as the process runs, independent of any
one conversation turn. `BillSplitterAgent` separately keeps the full message
history (system prompt, user turns, tool calls, tool results) so the model
has conversational context across turns. Together, this means you can say
"Rahul paid 900" in one message and "settle up" three messages later, and the
agent still has both the money and the context it needs — nothing is
re-explained by the user.

## Web frontend

Run the local browser frontend from this folder:

```bash
python web_app.py
```

Then open <http://127.0.0.1:8000>. The Groq API key stays on the server and is
loaded from `.env`; it is never sent to the browser. The page provides chat,
payment history, bill totals, a settlement plan, and a **New bill** reset
action. The existing `python app.py` terminal interface remains available.
Archived bills are saved locally in `.bill_history.json` when **New bill** is
clicked, and are shown in the Bill history panel after the server restarts.

If you open the frontend with VS Code Live Server at
<http://127.0.0.1:5500>, keep `python web_app.py` running on port 8000. The
frontend automatically sends API requests to the Python server.

