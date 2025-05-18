# How to Run MLGit

---

## Running Locally

```bash
poetry --directory /Users/andylee/Desktop/summer_2025/MLGit \
       run python -m mlgit.cli init
poetry --directory /Users/andylee/Desktop/summer_2025/MLGit \
       run python -m mlgit.cli index    
```

---

## Running Development Commands Locally

```bash
export MLGIT_DEV_MODE=1
poetry --directory /Users/andylee/Desktop/summer_2025/MLGit \
       run python -m mlgit.cli debug-graph
poetry --directory /Users/andylee/Desktop/summer_2025/MLGit \
       run python -m mlgit.cli debug-ast-results-retrieve
poetry --directory /Users/andylee/Desktop/summer_2025/MLGit \
       run python -m mlgit.cli debug-ast-results-retrieve -p "<file-pattern>"
```

---

## Installing Locally

```bash
poetry build
python3 -m venv /tmp/mlgit-v0-test1
source /tmp/mlgit-v0-test1/bin/activate
pip install dist/mlgit-0.1.0-py3-none-any.whl
mlgit init
mlgit index
```

---

## Activating Virtual Environment

```bash
source .venv/bin/activate
```

---

## Running Tests

```bash
pip install pytest # If not already installed
pytest
```
