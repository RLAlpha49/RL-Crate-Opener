import pyautogui
import pytesseract
import time
import keyboard
import pygetwindow as gw
from configparser import ConfigParser
from PIL import ImageGrab

# Initialize a dictionary to store the categories and counts
categories = {}
current_category = None
categories_config = ConfigParser()

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
            # Used to find different pixel rgb values within a certain area. I use this for finding out what rgb values to search for in the script.
            if color == (0, 0, 0):
                print(f"Pixel at ({x}, {y}) - Color: {pixel_color}")
            
            if color_match(pixel_color, color, shade):
                return x, y
    return None

def color_match(actual_color, target_color, shade):
    for i in range(3):
        if abs(actual_color[i] - target_color[i]) > shade:
            return False
    return True

# Function to save categorized items to a ConfigParser object
def save_to_config():
    for category, items in categories.items():
        categories_config[category] = items

if __name__ == "__main__":
    input("Press enter to start")
    time.sleep(0.1)
    
    # Register a hotkey (Ctrl + C) to save the results and exit the program
    keyboard.add_hotkey('ctrl+c', lambda: save_to_config() or exit(0))

    categories = {}  # Dictionary to temporarily store the categories and items

    if not pixel_search_in_window((38, 62, 107), 100, 100, 280, 281, shade=0):
        window = get_RL_window()
        print("Drop found")

        image = ImageGrab.grab(bbox=(window.left + 55, window.top + 335, window.left + 140, window.top + 350))
        text = pytesseract.image_to_string(image)
        print(text)

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
                categories.setdefault(current_category, {})
            else:
                # If there's no text on this line, it's an item under the current category
                if current_category and current_category != "Drops":
                    # Check if the item already exists in the dictionary
                    if line in categories[current_category]:
                        categories[current_category][line] += 1
                    else:
                        categories[current_category][line] = 1

        pyautogui.leftClick(window.left + 100, window.top + 280)
        time.sleep(1)

        i = 0
        while pixel_search_in_window((0, 2, 3), 70, 71, 920, 921, shade=0) and i < 3:
            i += 1
            pyautogui.leftClick(window.left + 165, window.top + 910)
            time.sleep(0.1)
            pyautogui.leftClick(window.left + 850, window.top + 610)
            time.sleep(8)

            image = ImageGrab.grab(bbox=(window.left + 725, window.top + 200, window.left + 1195, window.top + 240))
            text = pytesseract.image_to_string(image)
            print(text)

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
                    categories.setdefault(current_category, {})
                else:
                    # If there's no text on this line, it's an item under the current category
                    if current_category and current_category != "Drops":
                        # Check if the item already exists in the dictionary
                        if line in categories[current_category]:
                            categories[current_category][line] += 1
                        else:
                            categories[current_category][line] = 1

            pyautogui.leftClick(window.left + 1050, window.top + 990)
            time.sleep(0.5)
        print("No more Drop's left checking for more")
        pyautogui.leftClick(window.left + 130, window.top + 1030)
        time.sleep(0.5)

    # Remove the hotkey when the program is exiting
    keyboard.unhook_all()

    # Save the categorized items to a ConfigParser object
    save_to_config()

    # Write the ConfigParser object to a file
    with open('item_counts.ini', 'w') as configfile:
        categories_config.write(configfile)

    # Close the program gracefully
    exit(0)

    # pixel_search_in_window((0,0,0),100,500,280,281,shade=0)