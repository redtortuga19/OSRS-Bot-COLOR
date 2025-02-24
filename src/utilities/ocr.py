import pathlib
from operator import itemgetter
from typing import Dict, List, Union

import cv2
import numpy as np

import utilities.color as clr
import utilities.debug as debug
from utilities.geometry import Rectangle


def __load_font(font: str) -> Dict[str, cv2.Mat]:
    """
    Loads a font's alphabet from the fonts directory into a dictionary.
    Args:
        font: The name of the font to load.
    Returns:
        A dictionary of {"char": image} pairs.
    """
    PATH = pathlib.Path(__file__).parent.joinpath("fonts", font)
    pathlist = PATH.rglob("*.bmp")
    alphabet = {}
    for path in pathlist:
        name = int(path.stem)
        key = chr(name)
        value = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        alphabet[key] = value
    return alphabet


PLAIN_11 = __load_font("Plain11")  # Used by RuneLite plugins, small interface text (orbs)
PLAIN_12 = __load_font("Plain12")  # Chatbox text, medium interface text
BOLD_12 = __load_font("Bold12")  # Main text, top-left mouseover text, overhead chat
QUILL = __load_font("Quill")  # Large bold quest text
QUILL_8 = __load_font("Quill8")  # Small quest text


def extract_text(rect: Rectangle, font: dict, color: Union[clr.Color, List[clr.Color]], exclude_chars: Union[List[str], str] = "") -> str:
    """
    Extracts text from a Rectangle.
    Args:
        rect: The rectangle to search within.
        font: The font type to search for.
        color: The color(s) of the text to search for.
        exclude_chars: A list of characters to exclude from the search.
    Returns:
        A single string containing all text found in order, no spaces.
    """
    # Screenshot and isolate colors
    image = clr.isolate_colors(rect.screenshot(), color)
    result = ""
    char_list = []
    for key in font:
        if key == " " or key in exclude_chars:
            continue
        # Template match the character in the image
        correlation = cv2.matchTemplate(image, font[key], cv2.TM_CCOEFF_NORMED)
        # Locate the start point for each instance of this character
        y_mins, x_mins = np.where(correlation >= 0.98)
        # For each instance of this character, add it to the list
        char_list.extend([key, x, y] for x, y in zip(x_mins, y_mins))
    # Sort the char list based on which ones appear closest to the top-left of the image
    char_list = sorted(char_list, key=itemgetter(2, 1))
    # Join the charachers into a string
    return result.join(letter for letter, _, _ in char_list)


def find_text(
    text: Union[str, List[str]],
    rect: Rectangle,
    font: dict,
    color: Union[clr.Color, List[clr.Color]],
) -> List[Rectangle]:
    """
    Searches for exact text within a Rectangle. Input text is case sensitive.
    Args:
        text: The text to search for. Can be a phrase or a single word. You may also pass a list of strings to search for,
              but you cannot distinguish between them in the function output.
        rect: The rectangle to search within.
        font: The font type to search for.
        color: The color(s) of the text to search for.
    Returns:
        A list of Rectangles containing the coordinates of the text found.
    """
    # Screenshot and isolate colors
    image = clr.isolate_colors(rect.screenshot(), color)

    # Extract unique characters from input text
    chars = "".join(set("".join(text))).replace(" ", "")
    char_list = []
    for char in chars:
        try:
            template = font[char]
        except KeyError:
            text = text.replace(char, "")  # Remove characters that aren't in the font
            print(f"Font does not contain character: {char}. Omitting from search.")
            continue
        correlation = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        y_mins, x_mins = np.where(correlation >= 0.98)
        char_list.extend([char, x, y] for x, y in zip(x_mins, y_mins))

    # Sort the char list based on which ones appear closest to the top-left of the image
    char_list = sorted(char_list, key=itemgetter(2, 1))

    haystack = "".join(char[0] for char in char_list)

    words_found: List[Rectangle] = []

    if isinstance(text, str):
        text = [text]

    for word in text:
        word = word.replace(" ", "")
        for index, _ in enumerate(haystack):
            if haystack[index : index + len(word)] == word:
                # get the position of the first letter
                left, top = char_list[index][1], char_list[index][2]
                # get shape of last letter
                h, w = font[word[-1]].shape[:2]
                # get the width (height is the same for all letters)
                width = char_list[index + len(word) - 1][1] - left + w
                words_found.append(Rectangle(left + rect.left, top + rect.top, width, h))
                index += len(word)
    return words_found
