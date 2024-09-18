import io
import json
import sys
import pyodbc
import utils
import pandas as pd
from NLtoSQL import NLtoSQL
from typing import List
from tabulate import tabulate
import os
import anthropic
from cryptography.fernet import Fernet
import logging
import warnings

logging.getLogger('bokeh').setLevel(logging.ERROR)

# Suppress warnings
warnings.filterwarnings("ignore")


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
        self.__sql_retriever = None
        self.__claude_client = None
        self.__tries = tries
        self.__encryption_key = self.__get_or_create_key()

    def start_session(self):
        """
        Start an interactive session for querying databases.

        This method runs a loop that allows users to input natural language queries,
        get help, or exit the session.
        """
        utils.nice_print("Welcome to the SQL data retriever.\n"
                         "First, we need to set up your connection and API key:")

        if not self.__setup_connection():
            return

        if not self.__setup_api_key():
            return

        self.__sql_retriever = NLtoSQL(tries=2)
        self.__sql_retriever.connect_to_server(self.__connection)

        utils.nice_print("\nSetup complete! You can now start querying the database.\n"
                         "Type 'help' for explanation on how to write queries for this bot.\n"
                         "Type 'exit' or 'quit' to leave the session.\n")

        while True:
            question = input("How can I help you today?\n")
            if question.lower() in ['exit', 'quit']:
                break
            elif question.lower() == 'help':
                utils.nice_print(Terminal.HELP)
            else:
                if not self.__run_question(question):
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
        connection_file = utils.resource_path("Data/connection_info.json")
        connection_info = None
        while True:
            if os.path.exists(connection_file):
                with open(connection_file, "r") as f:
                    encrypted_info = json.load(f)
                    connection_info = {k: self.__decrypt(v) for k, v in encrypted_info.items()}
                utils.nice_print(f"""Found saved database information for '{connection_info["database"]}'!""")
                use_saved = input("Do you want to use the saved connection information? (y/n): ")
                if use_saved.lower() != 'y':
                    connection_info = None

            if not connection_info:
                connection_info = {
                    "server": input("Enter the SQL server address: "),
                    "database": input("Enter the database name: "),
                    "port": input("Enter the port (leave blank for default): "),
                    "use_windows_auth": input("Use Windows Authentication? (y/n): ").lower() == 'y'
                }
                if not connection_info["use_windows_auth"]:
                    connection_info["username"] = input("Enter the username: ")
                    connection_info["password"] = input("Enter the password: ")

            drivers = [
                '{ODBC Driver 17 for SQL Server}',
                '{ODBC Driver 18 for SQL Server}',
                '{SQL Server Native Client 11.0}',
                '{SQL Server}'
            ]

            server = f"{connection_info['server']},{connection_info['port']}" if connection_info['port'] else \
            connection_info['server']

            for driver in drivers:
                try:
                    if connection_info["use_windows_auth"]:
                        conn_str = f'DRIVER={driver};SERVER={server};DATABASE={connection_info["database"]};Trusted_Connection=yes;'
                    else:
                        conn_str = f'DRIVER={driver};SERVER={server};DATABASE={connection_info["database"]};UID={connection_info["username"]};PWD={connection_info["password"]};'

                    conn_str += "Encrypt=yes;TrustServerCertificate=yes"

                    self.__connection = pyodbc.connect(conn_str, timeout=10)
                    utils.nice_print(f"Connection successful using {driver}")
                    break
                except pyodbc.Error as e:
                    utils.nice_print(f"Connection failed with {driver}")
            else:
                utils.nice_print("Could not connect using any available driver.")
                retry = input("Would you like to try again? (y/n): ")
                if retry.lower() != 'y':
                    return False

            if self.__connection:
                if not os.path.exists(connection_file):
                    save_info = input("Would you like to save this connection information for future use? (y/n): ")
                    if save_info.lower() == 'y':
                        encrypted_info = {k: self.__encrypt(str(v)) for k, v in connection_info.items()}
                        with open(connection_file, "w") as f:
                            json.dump(encrypted_info, f)
                        utils.nice_print("Encrypted connection information saved for future use.")
                return True

    def __setup_api_key(self):
        """
        Prompt the user for a Claude API key, validate it, and set it as an environment variable.
        If a saved API key exists, use that instead of prompting the user.

        Returns:
            bool: True if a valid API key was provided and set, False otherwise.
        """
        api_key_file = utils.resource_path("Data/claude_api_key.txt")

        while True:
            if os.path.exists(api_key_file):
                with open(api_key_file, "r") as f:
                    api_key = self.__decrypt(f.read()).strip()
                utils.nice_print("Found saved API key. Validating...")
            else:
                api_key = input("Enter your Claude API key: ")

            try:
                os.environ['ANTHROPIC_API_KEY'] = api_key
                self.__claude_client = anthropic.Anthropic()
                self.__claude_client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                utils.nice_print("API key validated successfully and set as an environment variable!")

                if not os.path.exists(api_key_file):
                    save_key = input("Would you like to save this API key for future use? (y/n): ")
                    if save_key.lower() == 'y':
                        with open(api_key_file, "w") as f:
                            f.write(self.__encrypt(str(api_key)))
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

    def __run_question(self, question):
        for i in range(self.__tries):
            if not question:
                return True
            sql_codes, tables, saved_code = self.__sql_retriever.apply(question)
            if sql_codes:
                for code in sql_codes:
                    print(code[0] + '\n')
                self.__handle_results(tables)
                user_satisfaction = input("Did this information answer your question? (y/n): ").lower()
                if user_satisfaction == 'y':
                    if not saved_code:
                        to_save = input("Do you want me to provide the same tables"
                                        " to similar question in the future? (y/n): ").lower()
                        if to_save == 'y':
                            self.__sql_retriever.save_question(question, sql_codes)
                    utils.nice_print("Thank you for using my service!\n")
                    return True
                elif i+1 != self.__tries:
                    explanation = input("Please explain what was wrong or what you expected to get: ")
                    question = self.__handle_unsatisfactory_answer(question, explanation)
            else:
                return False
        utils.nice_print("I am sorry I wasn't able to help you, I hope to do better in the future.\n")
        return True

    def __handle_results(self, tables):
        """
        Handle the results of a SQL query, displaying them and offering to save them.

        Args:
            tables (List[Tuple]): A list of tuples containing table name, headers, and data.
        """

        utils.nice_print("Here is a preview of the tables I extracted (limited to 5 rows): \n")
        for i, table in enumerate(tables):
            utils.nice_print(f"{i + 1}. {table[0]}")
            print(tabulate(table[1].head(), headers='keys', tablefmt='pretty', floatfmt='.2f'))

        question = input("Would you like to save any of these tables? (Y/N)\n")
        while question.lower() not in ['y', 'n']:
            question = input("Please answer only in (Y/N)\n")

        if question.lower() == 'y':
            picked_tables = self.__pick_tables(tables)
            saved_tables = utils.save_tables(picked_tables)


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

    def __handle_unsatisfactory_answer(self, question, explanation):
        prompt = f"""The user asked the following question: "{question}"
                The provided answer was not satisfactory. The user explained: "{explanation}"
                Please reformulate the original question to address the user's concerns and expectations.
                Return the reformulated answer inside <new_question> tags (VERY IMPORTANT)"""

        response = self.__claude_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        new_question = utils.get_tags_info(response.content[0].text.strip(), "new_question")
        utils.nice_print(f"I've reformulated your question as: '{new_question}'")
        proceed = input("Should I proceed with this new question? (y/n): ").lower()

        if proceed == 'y':
            return new_question
        else:
            utils.nice_print(f"I apologize that I wasn't able to help, try asking the question again.")
            return ""

    def __get_or_create_key(self):
        key_path = utils.resource_path("Data/encryption_key.key")
        if os.path.exists(key_path):
            with open(key_path, "rb") as key_file:
                return key_file.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as key_file:
                key_file.write(key)
            return key

    def __encrypt(self, data):
        f = Fernet(self.__encryption_key)
        return f.encrypt(data.encode()).decode()

    def __decrypt(self, data):
        f = Fernet(self.__encryption_key)
        return f.decrypt(data.encode()).decode()


if __name__ == '__main__':
    try:
        data_retriever = Terminal()
        data_retriever.start_session()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        input("Press Enter to exit...")