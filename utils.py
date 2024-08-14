import textwrap as tw
import re
import os
import sys


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


def save_tables(tables, saving_location):
    """
    Save selected tables to CSV files.

    Args:
        tables (List[Tuple]): A list of tuples containing table name, headers, and data.
        saving_location (String): A string of the location to save the tables.
    """
    csv_paths = []
    tables_dir = resource_path(saving_location)
    ensure_dir(tables_dir)

    for table in tables:
        csv_filename = f"{table[0]}.csv"
        csv_path = os.path.join(tables_dir, csv_filename)
        try:
            table[1].to_csv(csv_path)
            nice_print(f"""Table "{table[0]}" results saved to "{csv_path}" """)
            csv_paths.append(csv_path)
        except Exception as e:
            nice_print(f"Error saving table {table[0]}: {str(e)}")

    return csv_paths
