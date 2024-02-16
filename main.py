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


if __name__ == "__main__":
    while True:
        USER_INPUT = 0
        while USER_INPUT != 1:
            print("1: Open Drops\n2: Calulate Probabilities\n3: Close")
            USER_INPUT = int(input())
            if int(USER_INPUT) == 2:
                sort_text_file()
                calculate_probabilities()
            elif int(USER_INPUT) == 3:
                break
        if int(USER_INPUT) == 3:
            break

        time.sleep(1)

        # Register a hotkey (Ctrl + C) to save the results and exit the program
        keyboard.add_hotkey("ctrl+c", lambda: sys.exit(0))

        # Checks for a drop in menu
        while not pixel_search_in_window((38, 62, 107), (100, 100, 280, 281), shade=0):
            window = get_rl_window()

            image = ImageGrab.grab(
                bbox=(
                    window.left + 30,
                    window.top + 130,
                    window.left + 450,
                    window.top + 190,
                )
            )
            TEXT = pytesseract.image_to_string(image, config=CUSTOM_CONFIG, lang="eng")

            TEXT = (str(TEXT).strip()).lower()

            if TEXT != "rewarditems":
                print("No Drops Left")
                break

            print("\nDrop found\n")

            image = ImageGrab.grab(
                bbox=(
                    window.left + 40,
                    window.top + 320,
                    window.left + 160,
                    window.top + 350,
                )
            )
            # text = pytesseract.image_to_string(image)
            TEXT = pytesseract.image_to_string(image, config=CUSTOM_CONFIG, lang="eng")
            print((str(TEXT).lower()).title())

            # Split the extracted text into lines
            lines = TEXT.split("\n")

            # Loop through the lines and categorize items
            CURRENT_CATEGORY = None
            for line in lines:
                # Remove any leading/trailing whitespace
                line = line.strip()

                # If the line is not empty, set it as the current category
                if line:
                    CURRENT_CATEGORY = line

            pyautogui.leftClick(window.left + 100, window.top + 280)
            time.sleep(1)

            while pixel_search_in_window((0, 2, 3), (70, 71, 920, 921), shade=0):
                pyautogui.leftClick(window.left + 165, window.top + 910)
                time.sleep(0.1)
                pyautogui.leftClick(window.left + 850, window.top + 610)
                time.sleep(8)

                image = ImageGrab.grab(
                    bbox=(
                        window.left + 725,
                        window.top + 200,
                        window.left + 1195,
                        window.top + 240,
                    )
                )
                TEXT = pytesseract.image_to_string(image)

                # Split the extracted text into lines
                lines = TEXT.split("\n")

                # Loop through the lines and categorize items
                for line in lines:
                    # Remove any leading/trailing whitespace
                    line = line.strip()

                    # If the line is not empty, set it as the current category
                    if line:
                        print(f"Opened {(str(line).lower()).title()}\n")
                        update_items(CURRENT_CATEGORY, line)

                pyautogui.leftClick(window.left + 1050, window.top + 990)
                time.sleep(0.5)
            print("\nNo more Drop's left checking for more\n")
            sort_text_file()
            pyautogui.leftClick(window.left + 130, window.top + 1030)
            time.sleep(0.5)

    # Remove the hotkey when the program is exiting
    keyboard.unhook_all()

    # Close the program gracefully
    sys.exit(0)
