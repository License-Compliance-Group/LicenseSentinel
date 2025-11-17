from analyzer import packageMetadataFetcher
import os

print("Working directory:", os.getcwd())
print("File esiste?:", os.path.exists("requirements.txt"))


def main():
    file_path = "requirements.txt"
    finder = packageMetadataFetcher.PyMetadataBuilder(file_path)
    for pkg in finder:
        print(f"{pkg.package} | {pkg.license} | {pkg.link}")


if __name__ == "__main__":
    main()
