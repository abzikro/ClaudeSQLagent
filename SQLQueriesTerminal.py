import pyodbc
import utils
import pandas as pd
from NLtoSQL import NLtoSQL
from typing import List
from tabulate import tabulate
import os
server = 'DESKTOP-23IMM3A\\SQLEXPRESS'
database = 'GDB_01_TEST'
username = 'sa'
pwd = 'sa'


class SQLQueriesTerminal:
    """
    A class that provides a command-line interface for querying SQL databases using natural language.

    This class allows users to interact with multiple SQL databases, switch between them,
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

    def __init__(self, SQLconnections: List[pyodbc.Connection], tries=2):
        """
        Initialize the SQLQueriesTerminal instance.

        Args:
            SQLconnections (List[pyodbc.Connection]): A list of pyodbc connection objects to different databases.
            tries (int): The number of attempts to make when generating SQL queries (passed to NLtoSQL).
        """
        self.__databases = ""
        self.__connections = SQLconnections
        self.__sql_retriever = NLtoSQL()
        for i in range(len(self.__connections)):
            self.__databases += f'{i + 1}. ' + self.__connections[i].getinfo(pyodbc.SQL_DATABASE_NAME) + '\n'

    def start_session(self):
        """
        Start an interactive session for querying databases.

        This method runs a loop that allows users to input natural language queries,
        switch databases, get help, or exit the session.
        """
        utils.nice_print("Welcome to the SQL data retriever.\n"
                   "type 'help' for explanation on how to write queries for this bot.\n"
                   "type 'exit' or 'quit' to leave the session.\n"
                   "type 'change' to change data server\n")
        if not self.__sql_retriever.is_connected_to_server() and not self.__choose_database():
            return
        while True:
            question = input("How can I help you today?\n")
            if question.lower() in ['exit', 'quit']:
                break
            elif question.lower() == "change":
                self.__choose_database()
            elif question.lower() == 'help':
                utils.nice_print(SQLQueriesTerminal.HELP)
            # elif self.__check_question_validity2(question):
            else:
                sql_codes, tables = self.__sql_retriever.apply(question)
                if sql_codes:
                    self.__handle_results(sql_codes, tables)
                    utils.nice_print("Thank you for using my service.\n")
                else:
                    utils.nice_print("There was a problem retrieving the query you have asked for from the database.\n"
                                "Write 'help' to get a sense of what makes a request better.\n"
                            "To clarify, requests might fail even if they are suitable so"
                                "feel free to try again.\n")

    def __choose_database(self):
        """
        Prompt the user to choose a database from the available connections.

        Returns:
            bool: True if a database was successfully chosen, False otherwise.
        """
        database_index = 'a'
        while not (database_index.isdigit() and int(database_index) in range(1, len(self.__connections) + 1)):
            database_index = input("Please pick the database you want to retrieve data from:\n" + self.__databases)
            if database_index.lower() in ['exit', 'quit']:
                return False
        self.__sql_retriever.connect_to_server(self.__connections[int(database_index) - 1])
        return True

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
            #print(tabulate(table[2][:5], headers=table[1], tablefmt='psql') + '\n')
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
                from autoviz import AutoViz_Class
                for i,table in enumerate(saved_tables):
                    df = pd.read_csv(table, index_col=0, parse_dates=True)
                    dir_path = table.split('.')[0]
                    os.makedirs(dir_path, exist_ok=True)
                    for col in df.columns:
                        if utils.is_date_format(df[col]):
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                    AV = AutoViz_Class()
                    AV.AutoViz(filename="", dfte=df, chart_format='html', save_plot_dir=dir_path)

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

# if __name__ == '__main__':
#     connection1 = pyodbc.connect(
#         'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' +
#         server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + pwd + ';')
#     connection2 = pyodbc.connect(
#         'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' +
#         server + ';DATABASE=' + 'GDB_GBL_TEST' + ';UID=' + username + ';PWD=' + pwd + ';')
#
#     data_retriever = SQLQueriesTerminal([connection1, connection2])
#     data_retriever.start_session()
#     connection1.close()
