# 🧠 MLGit (Preview)

> A local, open-source codebase indexer that makes your code LLM-friendly — compressing, summarizing, and structuring large repositories for AI-powered tools.

---

## 🚀 What is MLGit?

MLGit is a lightweight tool that **summarizes your codebase into a structured, token-efficient, interpretable format** that can be consumed by LLMs, agents, and developer tools. Think of it like `.git/`, but for giving your code *context awareness* for AI.

MLGit turns your project into a format that large language models can reason about — even with large, unfamiliar, undocumented codebases.

---

## 🔧 Key Features

- 📄 **Function/Class Summarization**: Converts full definitions into structured summaries (signatures, docstrings, types, descriptions).
- ♻️ **Incremental Re-indexing**: Only re-indexes changed files via `git diff` or checksum — fast and cheap.
- 🧠 **LLM-Optimized Context Compression**: Reduces token cost by summarizing code before inference.
- 🔍 **Interpretable JSON Format**: Stores summaries in a `.mlgit/` folder — visible, inspectable, version-controllable.
- 💻 **Local & Offline**: 100% local by default — no cloud uploads, no centralized infra required.
- 🔌 **Tool-Agnostic Integration**: Works with any codegen platform (Cursor, CoPilot, Claude, GPT, custom agents).
- 🧑‍💻 **Great for Onboarding**: Use `.mlgit/` as natural-language documentation for new team members.

---

## 📁 Example Output

Given this Python module:

```python
API_VERSION = "v1"

def log_transaction(user_id: str, amount: float) -> None:
    print(f"User {user_id} paid ${amount:.2f}")

class PaymentProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def process(self, user_id: str, card_info: dict, amount: float) -> bool:
        log_transaction(user_id, amount)
        return True
```

MLGit produces the following `.mlgit/index.json`:

```json
{
  "file": "payment.py",
  "summary": {
    "variables": [
      {
        "name": "API_VERSION",
        "type": "str",
        "value": "\"v1\"",
        "description": "API version identifier for the payment module."
      }
    ],
    "functions": [
      {
        "name": "log_transaction",
        "signature": "def log_transaction(user_id: str, amount: float) -> None",
        "description": "Logs the transaction details for a user and amount."
      }
    ],
    "classes": [
      {
        "name": "PaymentProcessor",
        "description": "Handles payment processing using an API key.",
        "methods": [
          {
            "name": "__init__",
            "signature": "def __init__(self, api_key: str)",
            "description": "Initializes the processor with the given API key."
          },
          {
            "name": "process",
            "signature": "def process(self, user_id: str, card_info: dict, amount: float) -> bool",
            "description": "Processes a payment and logs the transaction. Returns True if successful."
          }
        ],
        "properties": [
          {
            "name": "api_key",
            "type": "str",
            "description": "The API key used for authenticating payment requests."
          }
        ]
      }
    ]
  }
}
```

---

## 📦 Installation (Coming Soon)

```bash
pip install mlgit
# or
git clone https://github.com/yourname/mlgit
cd mlgit
python setup.py install
```

---

## 🛠️ Usage

```bash
# Initialize MLGit index in your repo
mlgit init

# Generate index summaries
mlgit index

# Re-index only changed files
mlgit reindex

# View index
cat .mlgit/index.json
```

> Want to use it with an LLM agent? Just load `.mlgit/index.json` and pass summaries into your prompt as compressed context.

---

## 🤖 Use Cases

- 🧠 Use with open-source or local LLMs to understand/reuse large codebases
- ⚙️ Improve custom codegen agents by summarizing reusable functions/modules
- 📚 Auto-documentation and onboarding guides
- 💡 Add intelligence to CLI tools, AI plugins, or browser-based playgrounds

---

## 💬 Why Not Just Use Embeddings?

Embeddings are great for *retrieval* — but not for *interpretation*.

MLGit gives you **semantic summaries** in natural language, optimized for LLM input and review by humans. It’s versionable, readable, and doesn’t require a vector database.

---

## 🛡️ Privacy & Local First

MLGit stores everything **locally** — nothing is uploaded to any cloud by default. It’s ideal for:

- OSS maintainers
- Local AI workflows
- Enterprise security environments

---

## 🧱 Project Roadmap

- [ ] File/function/class summarizer
- [ ] CLI: `init`, `index`, `reindex`
- [ ] VSCode extension
- [ ] Multi-language support (Python, JS, Go, etc.)
- [ ] Plugin support for LLM agents (e.g. LangChain, LlamaIndex)
- [ ] Auto-sync with Git for CI indexing

---

## ❤️ Contributing

We’d love your help improving MLGit!

```bash
git clone https://github.com/yourname/mlgit
cd mlgit
# Make changes, run tests, submit PR!
```

Open issues, contribute improvements, or add support for new languages!

---

## 📄 License

MIT — free to use, fork, and modify.

---

## 👋 Acknowledgements

Inspired by years of frustration working with LLMs over large, undocumented codebases. Shoutout to the teams behind Git, Cursor, Sourcegraph, and all OSS LLM pioneers.

---

## 🌐 Links

- Website / Docs: _coming soon_
- Discord: _coming soon_
- Twitter: [@yourhandle](https://twitter.com/yourhandle)

---

