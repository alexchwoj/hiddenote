# hiddenote

A simple encrypted notepad application built with Python and PyQt6.

## Features

- **Encryption**: All notes are encrypted using password-based authentication
- **Markdown Support**: Write and preview markdown content
- **Cross-platform**: Available for Windows, Linux, and macOS
- **Auto-save**: Automatic saving of your work

## Requirements

- Python 3.7+
- PyQt6
- Additional dependencies listed in requirements.txt

### Linux Additional Requirements

For Ubuntu/Debian systems, install the following system dependencies:

```bash
sudo apt install -y libxcb-cursor0 libxcb-cursor-dev binutils python3.13-dev
```

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/alexchwoj/hiddenote.git
   cd hiddenote
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Building

The project includes build scripts for creating standalone executables:

- **Windows**: `build_windows.bat` or `python build.py --platform windows`
- **Linux**: `build_linux.sh` or `python build.py --platform linux`
- **macOS**: `build_macos.sh` or `python build.py --platform macos`
- **All platforms**: `python build.py --platform all --tag v1.0.0`


## Screenshots
<img width="1204" height="806" alt="image" src="https://github.com/user-attachments/assets/271a9340-4d2f-45fb-856e-0252506f74b7" />
<img width="1205" height="806" alt="image" src="https://github.com/user-attachments/assets/5d7129b7-0d5e-47d2-a24d-a6a0fce07876" />


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
