# KodeKloud Downloader

A Python script to download course content (Markdown & PDFs) from KodeKloud.

## Features
-   **Interactive Authentication**: Prompts for your session cookie (token) if `cookie.txt` is not found.
-   **Smart Content Extraction**: Converts HTML lesson pages to clean Markdown.
-   **Resource Downloading**: Automatically downloads embedded Images and PDFs.
-   **Flattened Structure**: Saves files directly in numbered module folders (e.g., `2. Core Concepts/Lesson.md`).
-   **Download All**: Option to download **ALL** your enrolled courses in one go.

## Prerequisites
-   Python 3.8+
-   `pipx` (Recommended for running without virtualenv management) or `pip`.

## How to Run

### Method 1: Using `pipx` (Recommended)
Run the script directly with dependencies:
```bash
pipx run ./kodekloud_downloader.py
```

### Method 2: Standard Python
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the script:
    ```bash
    python3 kodekloud_downloader.py
    ```

## Authentication
The script needs your KodeKloud **Session Cookie** to access your courses.

**Option A: Interactive Input (Easiest)**
1.  Run the script.
2.  When prompted, paste your `session-cookie` value.
    -   *To get this*: Open KodeKloud in your browser -> F12 (DevTools) -> Application -> Cookies -> `https://learn.kodekloud.com` -> Copy value of `session-cookie`.

**Option B: `cookie.txt` File**
1.  Export your cookies from KodeKloud using a browser extension (in Netscape format).
2.  Save the file as `cookie.txt` in the script directory.
3.  The script will load it automatically.

## Usage

1.  **List Courses**: The script will fetch and list all your enrolled courses.
2.  **Select Course**:
    -   Enter the number of a specific course (e.g., `1`).
    -   **OR** Enter `0` to **Download All Courses**.
3.  **Select Modules** (If a single course was selected):
    -   Enter `A` to download ALL modules.
    -   **OR** Enter a specific module number.
4.  **Download**: Content will be saved to the `Downloads/` directory, organized by Course and Module.

## Run on Another Server

To run this script on a VPS or another machine:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/aaemon/kodekloud-downloader.git
    cd kodekloud-downloader
    ```

2.  **Run the script**:
    *   **Option A (pipx)**:
        ```bash
        pipx run ./kodekloud_downloader.py
        ```
    *   **Option B (Standard)**:
        ```bash
        pip install -r requirements.txt
        python3 kodekloud_downloader.py
        ```

3.  **Authenticate**:
    The script will ask for your **Session Cookie**. copying it from your browser and pasting it into the terminal is the quickest way.
