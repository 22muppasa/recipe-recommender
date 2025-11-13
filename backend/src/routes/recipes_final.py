from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import os
import re
import random
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

recipe_bp = Blueprint('recipes', __name__)

# Global variables for loaded data
recipes_df = None
tfidf_vectorizer = None
tfidf_matrix = None
categories = []


def parse_r_list(r_string):
    """Parse R-style list notation c(...) into Python list."""
    if pd.isna(r_string) or not r_string:
        return []

    r_string = str(r_string).strip()

    # Handle simple string case (not wrapped in c())
    if not r_string.startswith('c('):
        if r_string.startswith('"') and r_string.endswith('"'):
            return [r_string[1:-1]]
        return [r_string]

    try:
        # Remove c( and )
        content = r_string[2:-1].strip()
        if not content:
            return []

        items = []
        current_item = ""
        in_quotes = False
        quote_char = None
        escape_next = False

        for char in content:
            if escape_next:
                current_item += char
                escape_next = False
            elif char == '\\':
                escape_next = True
                current_item += char
            elif char in ['"', "'"]:
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                current_item += char
            elif char == ',' and not in_quotes:
                item = current_item.strip()
                if item.startswith('"') and item.endswith('"'):
                    item = item[1:-1]
                elif item.startswith("'") and item.endswith("'"):
                    item = item[1:-1]
                if item:
                    items.append(item)
                current_item = ""
            else:
                current_item += char

        if current_item.strip():
            item = current_item.strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            elif item.startswith("'") and item.endswith("'"):
                item = item[1:-1]
            if item:
                items.append(item)

        return items

    except Exception as e:
        print(f"Error parsing R list '{r_string[:100]}...': {e}")
        return []


def extract_time_minutes(time_str):
    """Extract minutes from time string (e.g., PT30M, PT1H30M)."""
    if not time_str or pd.isna(time_str):
        return 30

    try:
        time_str = str(time_str).strip()
        if 'PT' in time_str:
            if 'H' in time_str and 'M' in time_str:
                hours_match = re.search(r'(\d+)H', time_str)
                minutes_match = re.search(r'(\d+)M', time_str)
                hours = int(hours_match.group(1)) if hours_match else 0
                minutes = int(minutes_match.group(1)) if minutes_match else 0
                return hours * 60 + minutes
            if 'H' in time_str:
                hours_match = re.search(r'(\d+)H', time_str)
                hours = int(hours_match.group(1)) if hours_match else 0
                return hours * 60
            if 'M' in time_str:
                minutes_match = re.search(r'(\d+)M', time_str)
                minutes = int(minutes_match.group(1)) if minutes_match else 30
                return minutes
        else:
            numbers = re.findall(r'\d+', time_str)
            if numbers:
                return int(numbers[0])
    except Exception as e:
        print(f"Error parsing time '{time_str}': {e}")

    return 30


def safe_float(val):
    """Safely convert to float; return None on failure."""
    try:
        if pd.isna(val) or val == '' or val is None:
            return None
        return float(val)
    except Exc
