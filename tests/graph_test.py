import pytest
import subprocess
import shutil
from pathlib import Path
from mlgit.core.utils import find_git_root
from mlgit.core.graph import build_import_graph

# List of test repositories
TEST_REPOS = [
    "https://github.com/techandy42/MLGit_Test_Repo_N1"
]

@pytest.fixture(scope="session")
def test_repos_dir(tmp_path_factory):
    """Create a temporary directory for test repositories."""
    # Create a directory for test repos under the tests directory
    test_dir = Path(__file__).parent / "test_repos"
    test_dir.mkdir(exist_ok=True)
    return test_dir

@pytest.fixture(scope="session")
def cloned_repos(test_repos_dir):
    """Clone test repositories and yield their paths."""
    repo_paths = []
    
    for repo_url in TEST_REPOS:
        # Extract repo name from URL
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = test_repos_dir / repo_name
        
        # Clone if not already exists
        if not repo_path.exists():
            subprocess.run(
                ["git", "clone", repo_url, str(repo_path)],
                check=True,
                capture_output=True
            )
        
        repo_paths.append(repo_path)
    
    yield repo_paths
    
    # Cleanup after all tests are done
    for repo_path in repo_paths:
        if repo_path.exists():
            shutil.rmtree(repo_path)

def test_import_graph_building(cloned_repos):
    """Test building import graphs for cloned repositories."""
    for repo_path in cloned_repos:
        # Test that we can find the git root
        git_root = find_git_root()
        assert git_root is not None
        
        # Test building the import graph
        graph = build_import_graph(repo_path)
        print(graph)
        assert graph is not None
        # Add more specific assertions based on your graph structure
