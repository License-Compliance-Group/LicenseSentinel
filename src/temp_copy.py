"""
Analyzer Main Module
"""
import os
from analyzer import package_metadata_fetcher


print("Working directory:", os.getcwd())
print("File esiste?:", os.path.exists("requirements.txt"))


def main():
    file_path = "requirements.txt"
    finder = package_metadata_fetcher.build_package_metadata(file_path)
    # for pkg in finder:
    #    print(f"{pkg.package} | {pkg.license_type} | {pkg.link}")


if __name__ == "__main__":
    main()
