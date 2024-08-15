import textwrap as tw
import re
import os
import sys
import tkinter as tk
from tkinter import filedialog


def nice_print(text, width=120):
    """
    Wrap text while preserving existing newlines and structure. Used to make the output more readable.

    :param text: The text to wrap
    :param width: Maximum line width before wrapping (default 80)
    :return: Wrapped text as a single string
    """
    # Split the text into lines
    lines = text.split('\n')

    # Wrap each line individually
    wrapped_lines = []
    for line in lines:
        if line.strip() == '':
            wrapped_lines.append('')
        else:
            wrapped_lines.extend(tw.wrap(line, width=width))

    # Join the wrapped lines back together
    print('\n'.join(wrapped_lines))


def get_tags_info(massage, tag):
    start_tag = "<" + tag + ">"
    end_tag = "</" + tag + ">"

    start_index = massage.find(start_tag) + len(start_tag)
    end_index = massage.find(end_tag)

    return massage[start_index:end_index].strip()


def is_date_format(series):
    # Check if the column is object type and not empty
    if series.dtype == 'object' and not series.empty:
        # Check the first non-null value
        first_value = series.dropna().iloc[0]
        if isinstance(first_value, str):
            # Check if it matches YYYY-MM-DD format
            return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', first_value))
    return False


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_base_path():
    """Get the base path for the application, works both in development and when compiled"""
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running in normal Python environment
        return os.path.dirname(os.path.abspath(__file__))

def ensure_dir(directory):
    """Ensure that a directory exists, creating it if necessary"""
    if not os.path.exists(directory):
        os.makedirs(directory)



def save_tables(tables):
    """
    Save selected tables to CSV files, prompting for a location for each table.

    Args:
        tables (List[Tuple]): A list of tuples containing table name, headers, and data.
    """
    csv_paths = []
    # Create a root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)

    for table in tables:
        table_name, df = table

        # Prompt user for save location with a custom message
        file_path = filedialog.asksaveasfilename(
            parent=root,
            initialfile=f"{table_name}.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title=f"Save table '{table_name}'"
        )

        if file_path:  # If a file path was selected (user didn't cancel)
            try:
                df.to_csv(file_path, index=False)
                nice_print(f"""Table "{table_name}" saved to "{file_path}" """)
                csv_paths.append(file_path)
            except Exception as e:
                nice_print(f"Error saving table {table_name}: {str(e)}")
        else:
            nice_print(f"Saving cancelled for table {table_name}")

        # Destroy the root window
    root.destroy()

    return csv_paths
