# LicenseSentinel

A toolchain for building and analyzing the dependency tree of a Python project from its requirements. Includes software license analysis (scancode), license compatibility verification.

## Features

- **Dependency Tree Construction** – Builds a complete tree of dependencies (including transitive ones)
- **PyPI Metadata Retrieval** – Fetches license information from PyPI
- **License Compatibility Check** – Verifies compatibility between licenses using a compatibility matrix
- **Source Code Inspection** – Compares the license declared on PyPI with the one found in the original repository

## Requirements

### Python Dependencies

Install the project dependencies:

```bash
pip install -r src/requirements-dev.txt
```

### External Tool: ScanCode Toolkit

> ⚠️ **Important:** This project depends on **[ScanCode Toolkit](https://github.com/nexB/scancode-toolkit)** for source code license detection.

Install ScanCode separately:

```bash
pip install scancode-toolkit
```

Or download the pre-built binary from the [official releases](https://github.com/nexB/scancode-toolkit/releases) (⚠️ reccomaned).

## Usage

### For Users

If installed from PyPI:

```bash
licensesentinel
```

### For Developers

Run the TUI in development mode from the `src/` directory:

```bash
textual run --dev licensesentinel.py
```

## Project Structure

```
src/
├── entities/        # Domain layer: models & abstract interfaces
├── analyzer/        # Business logic layer
├── infrastructure/  # I/O layer: HTTP, filesystem, processes
└── interface/       # UI layer: GUI & controller
```

## License

See [LICENSE](LICENSE) for details.