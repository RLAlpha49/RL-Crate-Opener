# Rocket League Item Drop Automation

This project automates the process of opening item drops in Rocket League. It uses image recognition to detect item drops and categorize the items obtained from them. The results are then saved and probabilities are calculated.

## Installation

1. Clone this repository.
2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Before running the script, ensure the following:

- Set your screen resolution to 1920x1080p Borderless. The script will not work otherwise.
- Start the program on the "Drops" tab in your inventory.

Then, run the `main.py` script:

```bash
python main.py
```

The script will present you with a menu:

1. **Open Drops**: Start the automation process to open item drops.
2. **Calculate Probabilities**: Calculate the probabilities of obtaining each item.
3. **Close**: Exit the script.

During the automation process, you can press `Ctrl+C` to save the results and exit the program.

## Dependencies

This project uses the following Python packages:

- `keyboard`
- `pyautogui`
- `pytesseract`
- `Pillow`

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the terms of the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).
