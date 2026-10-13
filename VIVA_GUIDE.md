# Bill Splitter AI Agent - Viva Preparation Guide

This document explains the complete project in a viva-friendly way. Read the
**30-second introduction**, then revise the architecture, agent loop, and
settlement algorithm. The final section contains likely questions and answers.

---

## 1. 30-second project introduction

**Bill Splitter AI Agent** is an intelligent expense-sharing application. A
user can tell the system who paid how much, for example, "Rahul paid 900 for
dinner." The AI agent identifies the required action and calls a tool to
record that payment. When the user asks to settle the bill, the agent calls a
settlement tool. The tool calculates the total cost, equal share per person,
net balances, and the smallest practical set of repayments.

The project has:

1. A Python AI agent powered by Groq.
2. Two controlled tools: `add_share` and `settle_up`.
3. In-memory expense tracking.
4. A settlement algorithm based on debtor-creditor matching.
5. A browser frontend with chat, bill summary, payments, settlement plan, and
   bill history.
6. A local JSON archive for completed bills.

The important design principle is that the language model does not perform
financial arithmetic itself. It decides which tool to use, while deterministic
Python code performs the calculation.

---

## 2. Problem statement

When several people share expenses, manually calculating the fair share and
repayments is inconvenient and error-prone. A normal chatbot may also invent
payments or produce incorrect arithmetic.

This project solves the problem by combining:

- Natural-language interaction through an AI agent.
- Strict function/tool calling.
- Deterministic settlement logic.
- Persistent local history for completed bills.

The system supports examples such as:

```text
Rahul paid 900 for dinner.
Aman paid 600 for the same dinner.
Settle everything.
```

For two people, the result is that Aman owes Rahul ₹150.

---

## 3. Main objectives

- Accept expense information in natural language.
- Remember payments across multiple messages.
- Validate names and amounts.
- Avoid invented payments.
- Calculate the fair share accurately.
- Generate a small, understandable repayment plan.
- Explain the result conversationally.
- Provide a usable browser interface.
- Preserve completed bill summaries after starting a new bill.

---

## 4. High-level architecture

```text
User
  |
  v
Browser frontend
  |  HTTP JSON requests
  v
web_app.py
  |
  +--> BillSplitterAgent
  |       |
  |       +--> Groq LLM
  |       +--> Tool calls
  |
  +--> BillMemory
  |       |
  |       +--> Current expenses
  |
  +--> BillTools
  |       |
  |       +--> add_share()
  |       +--> settle_up()
  |
  +--> settlement.py
  |       |
  |       +--> totals
  |       +--> fair share
  |       +--> balances
  |       +--> repayments
  |
  +--> .bill_history.json
          Completed bill summaries
```

The terminal interface in `app.py` uses the same agent, tools, and memory. The
browser interface is an additional frontend and does not replace the core
agent.

---

## 5. File-by-file explanation

### `agent.py`

Contains the `BillSplitterAgent` class.

Responsibilities:

- Load `GROQ_API_KEY` from `.env`.
- Create the Groq client.
- Maintain the conversation message history.
- Send messages and tool definitions to the language model.
- Detect tool calls in the model response.
- Execute the requested local tool.
- Send the tool result back to the model.
- Return the final natural-language answer.

The system prompt gives the model strict rules:

- Use `add_share` when a user reports a payment.
- Use `settle_up` for "who owes whom" or settlement requests.
- Do not invent payments.
- Do not manually calculate financial results.
- Explain tool errors instead of guessing.

### `tools.py`

Contains `BillTools` and the Groq-compatible `TOOLS` definitions.

#### `add_share(person, amount)`

This function:

1. Converts and trims the person's name.
2. Rejects an empty name.
3. Converts the amount to a float.
4. Rejects invalid numbers.
5. Rejects zero or negative amounts.
6. Stores the valid expense in `BillMemory`.
7. Returns a structured result containing success, a message, and expenses.

#### `settle_up()`

This function:

1. Checks whether any payment exists.
2. Reads expenses from memory.
3. Calls `calculate_settlement()`.
4. Returns the settlement result.

The model sees JSON-style function definitions describing the names, arguments,
and purpose of these tools. This allows the model to request actions without
directly modifying application state.

### `memory.py`

Contains `BillMemory`, the current bill's in-process storage.

It stores entries such as:

```python
[
    {"person": "Rahul", "amount": 900.0},
    {"person": "Aman", "amount": 600.0},
]
```

Important methods:

- `add_expense()` stores a payment.
- `get_expenses()` returns all payments.
- `has_expenses()` checks whether the bill is empty.
- `clear()` starts a fresh bill.
- `total()` calculates the total of recorded expenses.

This memory is intentionally simple and lasts while the web server process is
running. Completed bill summaries are separately saved by the web layer.

### `settlement.py`

Contains the deterministic financial logic:

- `calculate_balances()`
- `calculate_settlement()`

This logic is independent of the AI model and can be tested without an API
key.

### `web_app.py`

Provides the local web server using Python's standard-library
`http.server`.

The server provides:

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Browser frontend |
| `/styles.css` | GET | Frontend styling |
| `/app.js` | GET | Frontend behavior |
| `/api/state` | GET | Current bill, summary, and messages |
| `/api/history` | GET | Archived completed bills |
| `/api/chat` | POST | Send a message to the agent |
| `/api/reset` | POST | Archive current bill and start a new one |

The web server keeps one `BillMemory` and one agent session for the current
server process. A lock protects state while handling concurrent HTTP requests.

### `frontend/index.html`

Defines the user interface:

- Brand/header.
- New bill button.
- Conversation area.
- Message input.
- Quick prompt buttons.
- Current bill overview.
- Payment activity.
- Settlement plan.
- Bill history archive.

### `frontend/app.js`

Handles browser behavior:

- Sends chat requests with `fetch()`.
- Displays user and assistant messages.
- Updates totals and payment lists.
- Loads the current state after page load.
- Loads archived bills from `/api/history`.
- Sends the reset request.
- Escapes displayed text before inserting it into HTML.

### `frontend/styles.css`

Provides the visual design and responsive layout for desktop and mobile screen
sizes.

### `app.py`

Provides the original command-line interface. It is useful for demonstrating
the agent without the browser:

```bash
python app.py
```

### `demo.py` and `demo_notebook.ipynb`

Demonstrate the project. The direct tools can be tested without an API key,
while the live agent demo requires `GROQ_API_KEY`.

### `.bill_history.json`

Created automatically by the web application when the user clicks **New
bill**. It contains up to the latest 50 completed bill summaries and is
ignored by Git because it is local user data.

---

## 6. How one chat message is processed

Suppose the user sends:

```text
Rahul paid 900 for dinner.
```

The flow is:

1. The browser sends `POST /api/chat` with the message.
2. `web_app.py` validates that the message is not empty.
3. `BillSplitterAgent.chat()` appends the user message to its conversation.
4. The agent sends the conversation and available tools to Groq.
5. The model decides that `add_share` is required.
6. The model returns a tool call with:

   ```json
   {"person": "Rahul", "amount": 900}
   ```

7. `execute_tool()` invokes `BillTools.add_share()`.
8. `BillMemory` stores Rahul's payment.
9. The tool result is appended as a tool message.
10. The model receives the result and writes a user-friendly confirmation.
11. The API returns the answer plus updated bill state.
12. The browser updates the chat, totals, and payment activity.

For "Settle everything", the same loop happens, but the model calls
`settle_up()`. The deterministic settlement result is then used to generate
the final explanation.

---

## 7. Agent loop and tool calling

The agent has a maximum of eight model/tool steps per user message. Each step
does the following:

```text
Send conversation to model
        |
        v
Does the response contain a tool call?
   /              \
 no                yes
 |                  |
Return answer       Execute each tool call
                    |
                    v
              Append tool result
                    |
                    v
                 Repeat
```

The loop ends when the model returns a normal assistant message without a
tool call. The maximum step count prevents an accidental infinite loop.

Tool calling is safer than asking the model to directly edit a balance because
the application controls the functions and validates their arguments.

---

## 8. Settlement algorithm

Assume:

```text
Rahul paid ₹900
Aman paid ₹600
Priya paid ₹0
```

In the current interaction model, people are identified from recorded
payments. For the two recorded payers:

### Step 1: Calculate total

```text
total = 900 + 600 = ₹1500
```

### Step 2: Calculate fair share

```text
fair share = total / number of people
           = 1500 / 2
           = ₹750
```

### Step 3: Calculate net balance

```text
Rahul: 900 - 750 = +₹150
Aman:  600 - 750 = -₹150
```

- Positive balance means the person should receive money.
- Negative balance means the person owes money.
- Zero means the person is balanced.

### Step 4: Separate creditors and debtors

```text
creditors = [Rahul: ₹150]
debtors   = [Aman: ₹150]
```

### Step 5: Match debtors to creditors

The algorithm transfers the minimum of the debtor's remaining amount and the
creditor's remaining amount. The resulting repayment is:

```text
Aman pays Rahul ₹150
```

For multiple people, it repeatedly matches the current debtor and creditor,
reducing both remaining values until one side reaches zero, then moving to the
next person. This produces a compact repayment list rather than requiring
every person to pay every other person.

### Complexity

- Building totals and balances: `O(n)`.
- Matching debtors and creditors: `O(n)` after the lists are prepared.
- Memory usage: `O(n)`.

Here, `n` is the number of expense entries or people, depending on the step.

### Rounding

Amounts are converted to floats and displayed to two decimal places. Balances
and repayment amounts are rounded to two decimal places. A production payment
system should prefer integer paise or Python's `Decimal` type to avoid binary
floating-point edge cases.

---

## 9. Bill history design

Current expenses are held in `BillMemory`. They are not automatically
permanent. When **New bill** is clicked:

1. The current expenses are read.
2. A settlement summary is calculated.
3. A history record is created with:
   - UTC-based ID
   - Local display date
   - Total
   - People and their paid amounts
   - Settlement list
4. The latest 50 records are retained.
5. The records are written to `.bill_history.json`.
6. Current memory and conversation are cleared.

This is local persistence, not a multi-user database. It is appropriate for a
demo or local project but would need a database for deployment.

---

## 10. Error handling

The project handles errors at several layers:

- Missing `GROQ_API_KEY` produces a clear startup error.
- Empty names are rejected.
- Invalid amounts are rejected.
- Zero and negative amounts are rejected.
- Settlement with no payments returns an error result.
- Invalid JSON requests return HTTP 400.
- Empty chat messages return HTTP 400.
- Missing frontend files return HTTP 404.
- Unexpected agent failures return an explicit HTTP 500 response.
- Tool failures are returned to the model instead of silently ignored.

The browser displays request failures as assistant-style error messages so the
user knows that the operation did not succeed.

---

## 11. How to run the project

### Configure the API key

Copy `.env.example` to `.env` and set:

```env
GROQ_API_KEY=your_actual_key
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the browser version

```bash
python web_app.py
```

Open:

```text
http://127.0.0.1:8000
```

### Run the terminal version

```bash
python app.py
```

### Run the tool-only smoke test

```bash
python demo.py
```

The tool-only section does not require a Groq API key. The live agent section
does require one.

---

## 12. Important design decisions

### Why use an AI agent?

Users can express payments naturally instead of filling a rigid form. The
agent extracts the person and amount and chooses the correct operation.

### Why use tools?

Tools create a controlled boundary between language understanding and state
changes. The model can request `add_share`, but the Python function validates
the input before storing it.

### Why not let the model calculate?

Language models are not reliable calculators. Financial arithmetic should be
done by deterministic code that can be tested and inspected.

### Why retain message history?

It lets the user say "Settle it now" after giving payments in earlier turns.
The agent sees the previous conversation, while `BillMemory` stores the
authoritative financial data.

### Why use a local standard-library web server?

It keeps the demo lightweight and avoids adding a web framework dependency.
For a production application, Flask, FastAPI, authentication, a database,
and HTTPS would be more appropriate.

### Why use two memory layers?

Conversation memory and financial memory have different responsibilities:

- Agent messages provide language context.
- `BillMemory` provides structured, authoritative payments.

This separation prevents the application from relying only on text history
for financial state.

---

## 13. Limitations and future improvements

Current limitations:

- One shared bill per running server process.
- No login or multi-user isolation.
- Local JSON history is not a database.
- People who did not pay are not explicitly added as participants.
- Currency handling is primarily INR.
- Float arithmetic is acceptable for the demo but not ideal for finance.
- The app depends on the external Groq service for natural-language chat.
- No authentication or HTTPS is included.

Possible improvements:

- Add an explicit participant-management tool.
- Use `Decimal` or integer paise.
- Add SQLite/PostgreSQL persistence.
- Add user accounts and separate bills.
- Add bill names, categories, receipts, and timestamps.
- Add tests for unequal and multi-person settlements.
- Add streaming responses.
- Add retry and timeout policies for the model API.
- Deploy behind HTTPS with authentication.

---

## 14. Likely viva questions and answers

### Q1. What is the main purpose of this project?

**Answer:** It automates shared-expense tracking. Users report payments in
natural language, and the system calculates fair shares and repayments using
deterministic Python logic.

### Q2. Is this a chatbot or an agent?

**Answer:** It is an agent because it can decide which application tool to
call, execute that tool, observe the result, and continue the conversation.
The sequence is not hardcoded for every user sentence.

### Q3. Which LLM/API is used?

**Answer:** The project uses the Groq Python client and a configurable Groq
model. The API key is loaded from the `.env` file and is never exposed to the
browser.

### Q4. What tools does the agent have?

**Answer:** It has exactly two tools: `add_share(person, amount)` for
recording a payment and `settle_up()` for calculating balances and repayments.

### Q5. What happens when the user says "Rahul paid 900"?

**Answer:** The model identifies a payment and creates an `add_share` tool
call. The Python function validates Rahul and 900, stores the expense in
memory, and returns the result. The model then confirms it to the user.

### Q6. How is the fair share calculated?

**Answer:** The total of all recorded payments is divided by the number of
people who have recorded payments. Each person's net balance is their payment
minus the fair share.

### Q7. What does a positive balance mean?

**Answer:** A positive balance means that person paid more than their fair
share and should receive money.

### Q8. What does a negative balance mean?

**Answer:** A negative balance means that person paid less than their fair
share and owes money.

### Q9. How are repayments minimized?

**Answer:** Creditors and debtors are placed in separate lists. The algorithm
matches a debtor with a creditor using the minimum remaining amount, records
that transfer, and continues until all balances are settled.

### Q10. Does the LLM perform the settlement arithmetic?

**Answer:** No. The LLM only decides to call `settle_up`. The deterministic
`settlement.py` code performs the arithmetic, which is more reliable.

### Q11. Why is `BillMemory` needed if the agent has message history?

**Answer:** Message history is conversational context, while `BillMemory` is
structured financial state. Keeping them separate makes calculations
independent of how the model phrases previous messages.

### Q12. What happens if the amount is negative?

**Answer:** `add_share` rejects it and returns an explicit error saying that
the amount must be greater than zero. It is not stored.

### Q13. What happens if no payments exist and the user asks to settle?

**Answer:** `settle_up` returns a failure result stating that no payments have
been recorded. The model is instructed to explain that error instead of
guessing.

### Q14. What is the role of `max_steps`?

**Answer:** It limits the number of model/tool iterations for one request.
This prevents an accidental infinite agent loop and gives a clear fallback
message if the model never produces a final answer.

### Q15. How does the frontend communicate with Python?

**Answer:** The frontend uses HTTP and JSON. It sends messages to
`POST /api/chat`, reads current data from `GET /api/state`, reads archived
bills from `GET /api/history`, and starts a fresh bill with `POST /api/reset`.

### Q16. Why is the API key not in JavaScript?

**Answer:** Exposing the API key in frontend JavaScript would allow anyone
using the page to steal and misuse it. The browser talks only to the local
Python server, and the server calls Groq securely.

### Q17. How is bill history stored?

**Answer:** When the user starts a new bill, the previous summary is saved in
`.bill_history.json`. The latest 50 summaries are retained and loaded when the
server starts.

### Q18. Is the current history implementation suitable for production?

**Answer:** It is suitable for a local demonstration, but not production.
Production would need a real database, user authentication, concurrency
controls, backups, and access permissions.

### Q19. What is the time complexity of settlement?

**Answer:** Calculating totals and balances is `O(n)`, and the greedy matching
is also `O(n)` after preparing the debtor and creditor lists. Memory usage is
`O(n)`.

### Q20. What is a weakness of using `float` for money?

**Answer:** Binary floating-point numbers can represent some decimal values
approximately. For production financial software, I would use integer paise
or Python's `Decimal` type and define an explicit rounding policy.

### Q21. How would you test this project?

**Answer:** I would test validation, memory operations, settlement examples,
empty-state behavior, API endpoints, reset/history persistence, and the
agent's tool-call loop with mocked model responses. The settlement tests can
run without an API key.

### Q22. What bug was fixed in the original project?

**Answer:** `settle_up()` incorrectly attempted to call `get_expenses()` on the
tools object instead of the memory object. The correct call is
`self.memory.get_expenses()`. Direct tool testing helps catch this before it
appears inside an LLM conversation.

### Q23. What happens if the Groq API is unavailable?

**Answer:** The API request fails explicitly and the web frontend displays an
error. The application does not pretend that the payment was recorded if the
agent request fails. Tool-only settlement logic can still be tested locally.

### Q24. Can two users safely use this exact server at the same time?

**Answer:** No. This demo has one shared in-memory bill for the process. A
production design would associate bills with authenticated users or sessions
and store them in a database.

### Q25. What would you improve first?

**Answer:** I would first add explicit participants and switch money handling
to `Decimal` or integer paise. Then I would add database-backed,
user-specific bill history and automated tests for all settlement cases.

---

## 15. Short final answer for the examiner

> This project is an AI-powered bill splitter. The user describes payments in
> natural language, and the Groq-based agent chooses between two controlled
> tools: recording a payment or calculating a settlement. The financial
> calculation is not delegated to the language model; it is performed by
> deterministic Python code. The application maintains conversation memory and
> structured expense memory separately. A local web frontend communicates with
> the Python backend through JSON endpoints and displays chat, payments,
> totals, and repayments. Completed bills are archived locally in JSON. The
> current version is designed as a local demonstration, while production use
> would require a database, authentication, Decimal-based money handling, and
> multi-user isolation.

