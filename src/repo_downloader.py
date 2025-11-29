import re
import requests


GITHUB_REPO_REGEX = re.compile(
    r"^https?:\/\/github\.com\/([^\/]+)\/([^\/]+?)(?:\.git)?(?:\/.*)?$",
    re.IGNORECASE
)

#We could/should use a strategy pattern so we could download from multiple git providers
class RepoDownloader:
    """
    Utility class to download a GitHub repository as a ZIP given a repo URL and branch.

    Responsibilities:
    - Validate a GitHub repository URL.
    - Construct the canonical GitHub archive ZIP URL for a branch.
    - Perform a GET request with basic error handling.
    - Persist the ZIP file to disk.

    Typical usage:
        RepoDownloader.download_github_zip(
            repo_url="https://github.com/numpy/numpy",
            branch="main",
            output="numpy-main.zip"
        )

    Notes:
    - repo_url may or may not end with a trailing slash; it is normalized.
    - Raises ValueError on invalid repo_url; prints errors from network / IO failures.
    """

    @staticmethod
    def download_github_zip(repo_url: str, branch: str, output: str, timeout: int = 10) -> None:
        """
        Download a GitHub repository branch as a ZIP file.

        Args:
            repo_url (str): Base repository URL, e.g. https://github.com/owner/repo or with trailing slash.
            branch   (str): Branch name to download (e.g. main, master).
            output   (str): Path (filename) where the ZIP will be saved.
            timeout  (int): Seconds before the HTTP request times out.

        Raises:
            ValueError: If repo_url is not a valid GitHub repository URL.
        """
        if not GITHUB_REPO_REGEX.match(repo_url):
            raise ValueError("URL not valid")

        # Normalize trailing slash
        if not repo_url.endswith("/"):
            repo_url += "/"

        zip_url = f"{repo_url}archive/refs/heads/{branch}.zip"

        try:
            response = requests.get(zip_url, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print(
                f"Timeout: the server did not respond within {timeout} seconds.")
            return
        except requests.exceptions.ConnectionError:
            print("Connection error: unable to reach the server.")
            return
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error {response.status_code}: {e}")
            return
        except requests.exceptions.RequestException as e:
            print(f"Generic error during request: {e}")
            return

        try:
            with open(output, "wb") as f:
                f.write(response.content)
        except OSError as e:
            print(f"Error saving file ({output}): {e}")
