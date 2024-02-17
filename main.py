"""
This is the main module for the Rocket League item drop automation script.

This script automates the process of opening item drops in Rocket League. It uses image recognition
to detect item drops and categorize the items obtained from them. The results are then saved and
probabilities are calculated.

Functions:
    main: The main function of the script.
"""

import time
import sys

import keyboard
import pyautogui
import pytesseract
from PIL import ImageGrab

from data.items import update_items, calculate_probabilities, sort_text_file
from utils.image_utils import pixel_search_in_window
from utils.window_utils import get_rl_window

# Config for Tesseract-OCR to extract text more accurately
CUSTOM_CONFIG = (
    r"--oem 3 --psm 6 "
    r"-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789- "
)

# Define constants for magic numbers
DROP_CHECK_COORDS = (100, 100, 280, 281)
DROP_FOUND_COORDS = (40, 320, 160, 350)
ITEM_OPEN_COORDS = (725, 200, 1195, 240)


def grab_image(window, coords):
    """Grab an image from the specified window and coordinates."""
    return ImageGrab.grab(
        bbox=(
            window.left + coords[0],
            window.top + coords[1],
            window.left + coords[2],
            window.top + coords[3],
        )
    )


def extract_text(img):
    """Extract text from the specified image."""
    return (
        pytesseract.image_to_string(img, config=CUSTOM_CONFIG, lang="eng")
        .strip()
        .lower()
    )


def handle_user_input():
    """Handle user input and return the selected option."""
    while True:
        print("1: Open Drops\n2: Calculate Probabilities\n3: Close")
        try:
            selected_option = int(input())
            if selected_option in [1, 2, 3]:
                return selected_option
        except ValueError:
            pass
        print("Invalid input. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    while True:
        user_input = handle_user_input()
        if user_input == 2:
            sort_text_file()
            calculate_probabilities()
            continue
        if user_input == 3:
            break

        time.sleep(1)

        # Register a hotkey (Ctrl + C) to save the results and exit the program
        keyboard.add_hotkey("ctrl+c", lambda: sys.exit(0))

        # Checks for a drop in menu
        while not pixel_search_in_window((38, 62, 107), DROP_CHECK_COORDS, shade=0):
            WINDOW = get_rl_window()

            image = grab_image(WINDOW, (30, 130, 450, 190))
            text = extract_text(image)

            TEXT = (str(text).strip()).lower()

            if TEXT != "rewarditems":
                print("No Drops Left")
                break

            print("\nDrop found\n")

            image = grab_image(WINDOW, DROP_FOUND_COORDS)
            text = extract_text(image)

            print((str(text).lower()).title())

            # Split the extracted text into lines
            lines = text.split("\n")

            # Loop through the lines and categorize items
            CURRENT_CATEGORY = None
            for line in lines:
                # Remove any leading/trailing whitespace
                line = line.strip()

                # If the line is not empty, set it as the current category
                if line:
                    CURRENT_CATEGORY = line

            pyautogui.leftClick(WINDOW.left + 100, WINDOW.top + 280)
            time.sleep(1)

            while pixel_search_in_window((0, 2, 3), (70, 71, 920, 921), shade=0):
                pyautogui.leftClick(WINDOW.left + 165, WINDOW.top + 910)
                time.sleep(0.1)
                pyautogui.leftClick(WINDOW.left + 850, WINDOW.top + 610)
                time.sleep(8)

                image = grab_image(WINDOW, ITEM_OPEN_COORDS)
                text = extract_text(image)

                # Split the extracted text into lines
                lines = text.split("\n")

                # Loop through the lines and categorize items
                for line in lines:
                    # Remove any leading/trailing whitespace
                    line = line.strip()

                    # If the line is not empty, set it as the current category
                    if line:
                        print(f"Opened {(str(line).lower()).title()}\n")
                        update_items(CURRENT_CATEGORY, line)

                pyautogui.leftClick(WINDOW.left + 1050, WINDOW.top + 990)
                time.sleep(0.5)
            print("\nNo more Drop's left checking for more\n")
            sort_text_file()
            pyautogui.leftClick(WINDOW.left + 130, WINDOW.top + 1030)
            time.sleep(0.5)

    # Remove the hotkey when the program is exiting
    keyboard.unhook_all()

    # Close the program gracefully
    sys.exit(0)
