import pytest
import subprocess
import shutil
import json
from pathlib import Path
from mlgit.core.utils import find_git_root
from mlgit.core.graph import build_import_graph, serialize_import_graph

# List of test repositories
TEST_REPOS = [
    "https://github.com/techandy42/MLGit_Test_Repo_N1",
    "https://github.com/techandy42/MLGit_Test_Repo_N2",
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
        assert git_root is not None, "Failed to find git root directory"
        
        # Test building the import graph
        graph = build_import_graph(repo_path)
        assert graph is not None, "Failed to build import graph"
        
        # Serialize the graph using the dedicated function
        serialized_graph = serialize_import_graph(graph)
        
        # Check if import_graph.json exists in the repo
        import_graph_path = repo_path / "import_graph.json"
        if import_graph_path.exists():
            # Load the stored graph
            with open(import_graph_path) as f:
                stored_graph = json.load(f)

            # Compare the graphs
            assert serialized_graph == stored_graph, \
                "Built graph does not match stored import_graph.json"
