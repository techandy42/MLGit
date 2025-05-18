
# MLGit

**MLGit** is a lightweight, local, open-source tool designed to index your codebase into structured, natural language summaries, enhancing the interaction between your codebase and large language models (LLMs), agents, and developer tools.

Think of it as a `.mlgit/` directory, analogous to `.git/`, tailored for AI-driven code understanding and indexing.

---

## ✨ Features

- **Function/Class Summarization**: Generates structured summaries for functions and classes, including signatures, docstrings, types, and descriptions.
- **Incremental Re-indexing**: Efficiently updates indexing only for changed portions of your codebase.
- **Token-Efficient Output**: Optimized summaries for efficient LLM usage and context awareness.
- **Structured Output**: Provides consistently formatted data for streamlined automated analysis.

---

## 📦 Installation & 🚀 Usage & 🧪 Testing

Please check the `docs/MLGIT_USAGE_GUIDE.md`.

---

## 📁 Project Structure

- `mlgit/core/` – Core application logic.
- `mlgit/cli.py/` - Entry point for CLI tool.
- `mlgit/tests/` – Tests for verifying functionality.
- `docs/` – Project documentation and resources.
- `pyproject.toml` – Project dependencies and configurations.

---

## 📄 License

This project is licensed under the [Apache 2.0 License](LICENSE).

---

## 🤝 Contributing

Contributions are encouraged! Please open issues or submit pull requests for bug fixes or improvements.

---

## 📈 Progress

- [x]  Command Line Interface [Being able to execute the program in command line at an external location]
    - [ ]  Build a test for CLI commands later on
- [x]  Project Initializer Script
- [x]  AST Module Graph Analyzer
    - [x]  Create test repos
    - [x]  Build a test for the graph analyzer
    - [ ]  Create correct import graph for each test repo
    - [ ]  Pass the unit test
- [x]  CPU-Bound/IO-Bound Task Scheduler
    - [ ]  Build a test for the scheduler
- [ ]  AST Module Code Indexer
    - [ ]  Also make sure to capture imports of modules
- [ ]  LLM Docstring Generator
- [ ]  Incremental Commit Update Logic
- [ ]  Non-Python Files Analyzer & Description Generator
