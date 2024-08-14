import json
import pyodbc
import utils
import pandas as pd
from NLtoSQL import NLtoSQL
from typing import List
from tabulate import tabulate
import os
import anthropic


class Terminal:
    """
    A class that provides a command-line interface for querying SQL databases using natural language.

    This class allows users to connect to a SQL database, input a Claude API key,
    and execute queries generated from natural language input using the NLtoSQL class.

    Attributes:
        HELP (str): A string containing help information for users on how to formulate queries.
    """

    HELP = """When requesting data from an SQL server, please be specific. Instead of asking, "Can you give me information about our sales?" provide clear details, such as:

    1. Specify the user or department: e.g., "sales team" or "marketing department".
    2. Define the data needed: e.g., "total sales," "monthly sales breakdown," or "top-selling products."
    3. Set the time frame: e.g., "for the last quarter," "for the past year," or "from January to June 2023."
    4. Include any filters: e.g., "for the North region," "for product category A," or "for customers over 50 years old."
    5. If you know the name of the tables you are interested in, feel free to write them.

    Example: "Can you provide the total sales for the marketing department from January to June 2023, broken down by month, for the North region?"
    The more details you provide, the better the AI can help you get the right information, even if you don't know the exact table names or SQL terminology.
    """

    def __init__(self, tries=2):
        """
        Initialize the SQLQueriesTerminal instance.

        Args:
            tries (int): The number of attempts to make when generating SQL queries (passed to NLtoSQL).
        """
        self.__connection = None
        self.__claude_api_key = None
        self.__sql_retriever = None

    def start_session(self):
        """
        Start an interactive session for querying databases.

        This method runs a loop that allows users to input natural language queries,
        get help, or exit the session.
        """
        utils.nice_print("Welcome to the SQL data retriever.\n"
                         "First, we need to set up your connection and API key.\n")

        if not self.__setup_connection():
            return

        if not Terminal.setup_api_key():
            return

        self.__sql_retriever = NLtoSQL(tries=2)
        self.__sql_retriever.connect_to_server(self.__connection)

        utils.nice_print("Setup complete! You can now start querying the database.\n"
                         "Type 'help' for explanation on how to write queries for this bot.\n"
                         "Type 'exit' or 'quit' to leave the session.\n")

        while True:
            question = input("How can I help you today?\n")
            if question.lower() in ['exit', 'quit']:
                break
            elif question.lower() == 'help':
                utils.nice_print(Terminal.HELP)
            else:
                sql_codes, tables = self.__sql_retriever.apply(question)
                if sql_codes:
                    self.__handle_results(sql_codes, tables)
                    utils.nice_print("Thank you for using my service.\n")
                else:
                    utils.nice_print("There was a problem retrieving the query you have asked for from the database.\n"
                                     "Write 'help' to get a sense of what makes a request better.\n"
                                     "To clarify, requests might fail even if they are suitable so "
                                     "feel free to try again.\n")

        self.__connection.close()

    def __setup_connection(self):
        """
        Prompt the user for SQL server connection information and establish a connection.

        Returns:
            bool: True if connection was successfully established, False otherwise.
        """
        connection_file = utils.resource_path("connection_info.json")
        connection_info = None
        while True:
            if os.path.exists(connection_file):
                with open(connection_file, "r") as f:
                    connection_info = json.load(f)
                utils.nice_print(f"""Found saved connection information by the name {connection_info["database"]}.""")
                use_saved = input("Do you want to use the saved connection information? (y/n): ")
                if use_saved.lower() != 'y':
                    connection_info = None

            if not connection_info:
                connection_info = {
                    "server": input("Enter the SQL server address: "),
                    "database": input("Enter the database name: "),
                    "username": input("Enter the username: "),
                    "password": input("Enter the password: ")
                }

            try:
                self.__connection = pyodbc.connect(
                    'DRIVER={ODBC Driver 17 for SQL Server};'
                    f'SERVER={connection_info["server"]};'
                    f'DATABASE={connection_info["database"]};'
                    f'UID={connection_info["username"]};'
                    f'PWD={connection_info["password"]};'
                )
                utils.nice_print("Connection successful!")

                if not os.path.exists(connection_file):
                    save_info = input("Would you like to save this connection information for future use? (y/n): ")
                    if save_info.lower() == 'y':
                        with open(connection_file, "w") as f:
                            json.dump(connection_info, f)
                        utils.nice_print("Connection information saved for future use.")

                return True
            except pyodbc.Error as e:
                utils.nice_print(f"Connection failed: {str(e)}")
                if os.path.exists(connection_file):
                    os.remove(connection_file)
                    utils.nice_print("Removed invalid saved connection information.")
                retry = input("Would you like to try again? (y/n): ")
                if retry.lower() != 'y':
                    return False

    @staticmethod
    def setup_api_key():
        """
        Prompt the user for a Claude API key, validate it, and set it as an environment variable.
        If a saved API key exists, use that instead of prompting the user.

        Returns:
            bool: True if a valid API key was provided and set, False otherwise.
        """
        api_key_file = utils.resource_path("claude_api_key.txt")

        while True:
            if os.path.exists(api_key_file):
                with open(api_key_file, "r") as f:
                    api_key = f.read().strip()
                utils.nice_print("Found saved API key. Validating...")
            else:
                api_key = input("Enter your Claude API key: ")

            try:
                os.environ['ANTHROPIC_API_KEY'] = api_key
                client = anthropic.Anthropic()
                client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                utils.nice_print("API key validated successfully and set as an environment variable!")

                if not os.path.exists(api_key_file):
                    save_key = input("Would you like to save this API key for future use? (y/n): ")
                    if save_key.lower() == 'y':
                        with open(api_key_file, "w") as f:
                            f.write(api_key)
                        utils.nice_print("API key saved for future use.")

                return True
            except Exception as e:
                utils.nice_print(f"API key validation failed: {str(e)}")
                if os.path.exists(api_key_file):
                    os.remove(api_key_file)
                    utils.nice_print("Removed invalid saved API key.")
                retry = input("Would you like to try again? (y/n): ")
                if retry.lower() != 'y':
                    return False


    def __handle_results(self, SQLcodes, tables):
        """
        Handle the results of a SQL query, displaying them and offering to save them.

        Args:
            SQLcodes (List[str]): A list of SQL queries executed.
            tables (List[Tuple]): A list of tuples containing table name, headers, and data.
        """
        use_sql = input("A preview of the tables will be shortly given to you, would you like to get the sql code with them? (Y/N)")
        use_sql = True if use_sql.lower() == 'y' else False
        utils.nice_print("Here is a preview of the tables I extracted (limited to 5 rows): \n")
        for i, table in enumerate(tables):
            utils.nice_print(f"{i + 1}. {table[0]}")
            print(tabulate(table[1].head(), headers='keys', tablefmt='pretty'))
            if use_sql:
                utils.nice_print("SQL code used:\n" + SQLcodes[i])

        question = input("Would you like to save any of these tables? (Y/N)\n")
        while question.lower() not in ['y', 'n']:
            question = input("Please answer only in (Y/N)\n")

        if question.lower() == 'y':
            picked_tables = self.__pick_tables(tables)
            saved_tables = utils.save_tables(picked_tables, "Tables")
            question = input("Would you like an automated visualization of the saved tables? (Y/N)\n")
            while question.lower() not in ['y', 'n']:
                question = input("Please answer only in (Y/N)\n")
            if question.lower() == 'y':
                from bokeh.plotting import figure
                from autoviz import AutoViz_Class
                figure(width=1200, height=900)
                for i, table in enumerate(saved_tables):
                    df = pd.read_csv(table, index_col=0, parse_dates=True)
                    dir_path = utils.resource_path(table.split('.')[0])
                    utils.ensure_dir(dir_path)
                    for col in df.columns:
                        if utils.is_date_format(df[col]):
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                    AV = AutoViz_Class()
                    AV.AutoViz(filename="", dfte=df, chart_format='png', save_plot_dir=dir_path, verbose=2)

    def __pick_tables(self, tables):
        while True:
            table_choices = input(
                "Enter the numbers of the tables you want to save (comma-separated), or 'all' for all tables: \n")
            if table_choices.lower() == 'all':
                return tables
            try:
                tables_to_save = [int(choice.strip()) - 1 for choice in table_choices.split(',')]
                if all(0 <= i < len(tables) for i in tables_to_save):
                    return [tables[i] for i in tables_to_save]
                else:
                    print("Invalid table number(s). Please try again.\n")
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas or 'all'.\n")

if __name__ == '__main__':
    try:
        data_retriever = Terminal()
        data_retriever.start_session()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        input("Press Enter to exit...")