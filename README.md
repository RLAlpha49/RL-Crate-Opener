# Rocket League Item Drop Automation

This project automates the process of opening item drops in Rocket League. It uses image recognition to detect item drops and categorize the items obtained from them. The results are then saved and probabilities are calculated.

## Installation

1. Clone this repository.
2. Create a Python virtual environment (recommended):

    ```bash
    # Windows (PowerShell)
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    
    # or Windows (Command Prompt)
    python -m venv venv
    venv\Scripts\activate.bat
    
    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

4. Ensure Tesseract OCR is installed on your system:
   - **Windows**: Download and install from [GitHub Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)

## Configuration

All application settings are defined in `config.py`. Key settings include:

- **Screen Resolution**: Must be exactly 1920x1080p Borderless
- **Screen Regions**: Configurable regions for detecting drops, rewards, and items
- **Click Coordinates**: Precise coordinates for automating clicks
- **Colors**: RGB values for pixel-based detection
- **OCR Settings**: Tesseract configuration with optional retry logic and debug dumps
- **Timing**: Animation delays and click intervals
- **Color Tolerance**: Shade tolerance for color matching (default: 10)
- **Window Cache Refresh**: How often to refresh window geometry (default: every 10 iterations)
- **Debug Options**: Enable image dumps for troubleshooting

### Items File Path Resolution

The `ITEMS_FILE` configuration (default: `items.txt`) is resolved as follows:

- **Absolute paths**: Used as-is
- **Relative paths**: Anchored to the project root (repository directory) for deterministic behavior regardless of where the script is invoked

This ensures the items file is always persisted to the same location, making the application portable and independent of the current working directory.

### Persistent Settings

Settings can be saved to a `settings.json` file in the project root, allowing them to persist across program restarts. This works with both CLI and GUI applications.

#### How to Configure Persistent Settings

**GUI Method** (Recommended):

1. Run the GUI: `python main_gui.py`
2. Open **Tools → Settings**
3. Modify settings as desired
4. Click **Save and Apply**
5. Settings are now saved to `settings.json` and will load automatically on next program start

**Manual Method**:
Create a `settings.json` file in the project root with your desired settings:

```json
{
  "RL_DEBUG_DUMP_IMAGES": "false",
  "RL_DEBUG_DIR": "debug_images",
  "RL_LOG_LEVEL": "INFO",
  "RL_LOG_FILE": "C:\\path\\to\\app.log",
  "RL_COLOR_SHADE_TOLERANCE": "15",
  "RL_INITIAL_DELAY": "2.0",
  "RL_TESSERACT_CMD": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
}
```

#### Setting Priority

Environment variables follow this precedence (highest to lowest):

1. **Shell environment variables** - Set in terminal/PowerShell before running (overrides all)
2. **Saved settings file** (`settings.json`) - User-configured preferences
3. **Hardcoded defaults** - Built into the application

This means:

- If you set an environment variable in your terminal, it will override the saved settings
- If no environment variable is set, the saved settings file will be loaded
- If neither exists, the hardcoded defaults are used

### Environment Variable Overrides

You can override configuration values using environment variables. Set them before running the script:

#### Windows (PowerShell)

```powershell
$env:RL_DEBUG_DUMP_IMAGES = "true"
$env:RL_COLOR_SHADE_TOLERANCE = "15"
$env:RL_INITIAL_DELAY = "2.0"
python main.py
```

#### Supported Environment Variables

All variables use the `RL_` prefix:

- **`RL_DEBUG_DUMP_IMAGES`**: Set to `"true"` to enable debug failed image dumping to `debug_images/sessions/` (default: false)
- **`RL_DEBUG_DUMP_ALWAYS`**: Set to `"true"` to dump debug images for all OCR operations, not just failed ones (default: false)
- **`RL_DEBUG_DIR`**: Directory path for saving debug images (default: `debug_images`)
- **`RL_DEBUG_MAX_IMAGES`**: Maximum number of debug images to save per session; 0 means unlimited (default: 0)
- **`RL_DEBUG_IMAGE_FORMAT`**: Image format for debug dumps (PNG or JPEG, default: PNG)
- **`RL_DEBUG_JPEG_QUALITY`**: JPEG quality for debug images 1-100 (default: 85)
- **`RL_COLOR_SHADE_TOLERANCE`**: Integer tolerance for color matching (default: 10)
- **`RL_DROP_CHECK_TOLERANCE`**: Integer tolerance for drop check pixel matching (default: 10)
- **`RL_OPEN_BUTTON_TOLERANCE`**: Integer tolerance for open button pixel matching (default: 10)
- **`RL_INITIAL_DELAY`**: Initial delay before starting automation in seconds (float, default: 1.0)
- **`RL_DROP_CHECK_INTERVAL`**: Interval for checking if item view is ready in seconds (float, default: 8.0). Set to `3.5` if using the BakkesMod DisableCrateAnim plugin to align with animation timing (default: 8.0)
- **`RL_ITEMS_FILE`**: Path to items file (default: `items.txt` in project root)
- **`RL_WINDOW_CACHE_REFRESH_INTERVAL`**: How often to refresh window cache in iterations (int, default: 10)
- **`RL_TESSERACT_CMD`**: Path to Tesseract OCR executable (Windows example: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
  - Only needed if Tesseract is not in your system PATH
- **`RL_LOG_LEVEL`**: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
- **`RL_LOG_TO_FILE`**: Set to `"true"` to enable session-specific file logging during automation (default: false)
- **`RL_LOG_FILE`**: Global immediate file logging path. Set to a file path to enable logging to that file immediately for the entire application lifecycle (default: empty, disabled)

#### Example with Tesseract Configuration

```powershell
$env:RL_DEBUG_DUMP_IMAGES = "true"
$env:RL_TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:RL_COLOR_SHADE_TOLERANCE = "15"
$env:RL_INITIAL_DELAY = "2.0"
python main.py
```

## Usage

Before running the script, ensure the following:

- Set your screen resolution to **1920x1080p Borderless**. The script will not work otherwise.
- Start with Rocket League on the **"Drops" tab** in your inventory.

Run the main script:

```bash
python main.py
```

The script will present you with an interactive menu:

1. **Open Drops**: Start the automation process to open and categorize item drops.
2. **Run Calibration**: Verify that configuration values correctly target screen elements.
3. **Calculate Probabilities**: Calculate and display drop probabilities for all categories.
4. **Exit**: Close the application.

## GUI Usage (Alternative Interface)

The application offers a modern graphical interface as an alternative to the CLI. Both interfaces provide the same automation functionality, but the GUI offers real-time visual feedback through dedicated panels for progress tracking, log viewing, and statistics display.

### Prerequisites

- Screen resolution set to **1920x1080p Borderless**
- Rocket League on the **"Drops" tab** in inventory
- PyQt6 must be installed (already included in `requirements.txt`)

### Launching the GUI

To start the GUI application, run:

```bash
python main_gui.py
```

The GUI window will open with four resizable panels providing comprehensive automation controls and monitoring.

### During Automation

- You can press **`Ctrl+C`** to gracefully shutdown and save progress.
- Items are automatically sorted by rarity and name after each drop.
- Drop data is persisted to `items.txt` (or custom path via `RL_ITEMS_FILE`) and is retained across sessions.

## Performance Optimization with BakkesMod

For significantly faster drop opening, consider installing the **BakkesMod DisableCrateAnim plugin**:

- **Plugin**: [BakkesMod DisableCrateAnim Plugin](https://bakkesplugins.com/plugin/586)
- **What it does**: Cuts the item reveal animation duration in half (from ~8 seconds to ~4 seconds)
- **How to use with this script**:
  1. Install the BakkesMod DisableCrateAnim plugin following the link above
  2. Enable it in BakkesMod
  3. Set the `RL_DROP_CHECK_INTERVAL` environment variable to `3.5` before running the script:

```powershell
$env:RL_DROP_CHECK_INTERVAL = "3.5"
python main.py
```

This synchronizes the script's item detection timing with the accelerated animation, allowing it to process drops faster while maintaining reliability.

**Default behavior** (without DisableCrateAnim): The script waits 8 seconds between checks, which is safe for standard animation timing.

## Debug Options

Debug features can be enabled via environment variables to help troubleshoot issues:

### Enable Debug Image Dumps

Use the environment variable to enable debug image dumps:

```powershell
$env:RL_DEBUG_DUMP_IMAGES = "true"
python main.py
```

This will save all OCR input images to the `debug_images/sessions/<session_id>/` directory.

When `RL_DEBUG_DUMP_IMAGES` is enabled, the default per-session limit is unlimited (0). To limit the number of debug images per session, use:

```powershell
$env:RL_DEBUG_DUMP_IMAGES = "true"
$env:RL_DEBUG_MAX_IMAGES = "100"
python main.py
```

This prevents excessive disk usage by limiting the session to 100 images. Set `RL_DEBUG_MAX_IMAGES` to 0 (default) for unlimited images.

### Enable File Logging

There are two ways to enable file logging:

1. **RL_LOG_FILE** (global, immediate): Set this to a specific file path to enable logging to that file globally and immediately for the entire application lifecycle.

   ```powershell
   $env:RL_LOG_FILE = "C:\path\to\app.log"
   python main.py
   ```

   This enables file logging immediately and applies to the entire application lifecycle.

2. **RL_LOG_TO_FILE** (session-based, automation-specific): Set this during automation to create a session-specific log file.

   ```powershell
   $env:RL_LOG_TO_FILE = "true"
   $env:RL_LOG_LEVEL = "DEBUG"
   python main.py
   ```

   When you choose "Open Drops", a session log is created at `debug_images/logs/automation_<timestamp>.log`.
   The `RL_LOG_LEVEL` setting applies to both logging methods and controls verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).

Logs can be inspected to track the automation flow and identify where issues occur.

**Note for Developers**: If you need to programmatically override configuration for testing, use the `with_overrides()` method on the CONFIG object:

```python
from src.config import CONFIG

# Create a modified config (doesn't mutate the original)
test_config = CONFIG.with_overrides(DEBUG_DUMP_IMAGES=True, LOG_LEVEL="DEBUG")
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
