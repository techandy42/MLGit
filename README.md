# MLGit (Under Development)

---

## Running Locally

```bash
poetry --directory /Users/andylee/Desktop/summer_2025/MLGit \
       run python -m mlgit.cli init
poetry --directory /Users/andylee/Desktop/summer_2025/MLGit \
       run python -m mlgit.cli index    
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

