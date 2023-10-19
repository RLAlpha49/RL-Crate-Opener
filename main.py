import pyautogui
import pytesseract
import time
import keyboard
import os
import sys
import pygetwindow as gw
from configparser import ConfigParser
from PIL import ImageGrab

def get_RL_window():
    # Find the Rocket League window by its title
    window = gw.getWindowsWithTitle("Rocket League")[0]
    return window

def pixel_search_in_window(color, left, right, top, bottom, shade=None):
    window = get_RL_window()
    screenshot = ImageGrab.grab(bbox=(window.left, window.top, window.left + 1920, window.top + 1080))

    for x in range(left, right):
        for y in range(top, bottom):
            pixel_color = screenshot.getpixel((x, y))
            if color_match(pixel_color, color, shade):
                return x, y
    return None

def color_match(actual_color, target_color, shade):
    for i in range(3):
        if abs(actual_color[i] - target_color[i]) > shade:
            return False
    return True

# Gets directory of program
base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
items_file_path = os.path.join(base_dir, "items.txt")

def load_items():
    items = ConfigParser()
    items.read(items_file_path)
    return items

def update_items(category, item):
    items = load_items()

    # Ensure the category exists
    if not items.has_section(category):
        items.add_section(category)

    # Ensure the item exists within the category
    if items.has_option(category, item):
        items.set(str(category), str(item), str(int(items.get(str(category), str(item))) + 1))
    else:
        items.set(category, str(item), "1")

    with open(items_file_path, "w") as configfile:
        items.write(configfile)
        
def calculate_probabilities():
    categories = load_items()
    
    for category in categories.sections():
        print(f'Category: {category}')
        # Gets total number of items in category
        total_items = sum([int(count) for count in categories[category].values()])
        
        # Creates a list of amount of items with rarity
        rarities = {
            "Uncommon": 0,
            "Rare": 0,
            "Very Rare": 0,
            "Import": 0,
            "Exotic": 0,
            "Black Market": 0
        }
        
        # Adds items to their respective rarity
        for item, count in categories[category].items():
            rarity = get_rarity(item)  # Function to extract rarity from item name
            rarities[rarity] += int(count)
        
        # Calculate probabilities
        for rarity, count in rarities.items():
            probability = count / total_items
            # Will not print probabilities of 0%
            if probability > 0:
                print(f'{rarity}: {probability * 100:.2f}%')
        
        print()

# Function to extract rarity from an item name
def get_rarity(item):
    rarities = ["Uncommon", "Very Rare", "Rare", "Import", "Exotic", "Black Market"]
    for rarity in rarities:
        if rarity.lower() in item.lower():
            return rarity
    return "Unknown"  # If rarity is not recognized

if __name__ == "__main__":
    user_input = 0
    while user_input != 1:
        print("1: Open Drops\n2: Calulate Probabilities")
        user_input = int(input())
        if int(user_input) == 2:
            calculate_probabilities()
    
    time.sleep(1)
    
    # Register a hotkey (Ctrl + C) to save the results and exit the program
    keyboard.add_hotkey('ctrl+c', lambda: exit(0))

    # Checks for a drop in menu
    while not pixel_search_in_window((38, 62, 107), 100, 100, 280, 281, shade=0):
        window = get_RL_window()
        print("\nDrop found\n")

        image = ImageGrab.grab(bbox=(window.left + 40, window.top + 335, window.left + 160, window.top + 350))
        text = pytesseract.image_to_string(image)
        
        # Split the extracted text into lines
        lines = text.split('\n')

        # Loop through the lines and categorize items
        current_category = None
        for line in lines:
            # Remove any leading/trailing whitespace
            line = line.strip()

            # If the line is not empty, set it as the current category
            if line:
                current_category = line

        pyautogui.leftClick(window.left + 100, window.top + 280)
        time.sleep(1)

        while pixel_search_in_window((0, 2, 3), 70, 71, 920, 921, shade=0):
            pyautogui.leftClick(window.left + 165, window.top + 910)
            time.sleep(0.1)
            pyautogui.leftClick(window.left + 850, window.top + 610)
            time.sleep(8)

            image = ImageGrab.grab(bbox=(window.left + 725, window.top + 200, window.left + 1195, window.top + 240))
            text = pytesseract.image_to_string(image)

            # Split the extracted text into lines
            lines = text.split('\n')

            # Loop through the lines and categorize items
            for line in lines:
                # Remove any leading/trailing whitespace
                line = line.strip()

                # If the line is not empty, set it as the current category
                if line:
                    print(f"Opened {(str(line).lower()).title()}\n")
                    update_items(current_category, line)
                    

            pyautogui.leftClick(window.left + 1050, window.top + 990)
            time.sleep(0.5)
        print("\nNo more Drop's left checking for more\n")
        pyautogui.leftClick(window.left + 130, window.top + 1030)
        time.sleep(0.5)

    # Remove the hotkey when the program is exiting
    keyboard.unhook_all()

    # Close the program gracefully
    exit(0)