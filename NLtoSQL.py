import anthropic
import utils
from QuestionDatabase import QuestionDatabase
from utils import nice_print, get_tags_info
import pandas as pd


class NLtoSQL:
    """
    A class that converts natural language questions to SQL queries using the Anthropic API.

    This class connects to a SQL database, interprets natural language questions,
    generates appropriate SQL queries, and executes them to retrieve data.

    Attributes:
        MISSION1_PROMPT (str): File path for the first mission prompt.
        MISSION2_PROMPT (str): File path for the second mission prompt.
        FIXER2 (str): A template for fixing erroneous SQL code.
    """
    # List of tables to always include
    ESSENTIAL_TABLES = [
        'WO_HDR', 'WO_LINE', 'SO_HDR', 'SO_LINE', 'PO_HDR', 'PO_LINE',
        'STOCK', 'STOCKWH', 'STOCKWHUPD', 'TKT_LINE', 'PSHIP_LINE',
        'CLM_LINE', 'WOMNT_LINE', 'STOCKWHTRANSFER_LINE', 'SRCV_LINE',
        'RCV_LINE', 'RMA_LINE', 'INSPECTION_BY_ACCOUNT', 'TBLCODE',
        'CUSTVEND', 'CUSTVENDSETUP', 'INSPECTION_BY_VENDOR_RATE',
        'INSEPCTION_BY_PARTNUMBER', 'WHLIST'
    ]
    SIMILAR_QUESTION_PROMPT = utils.resource_path("Prompt_helpers/SIMILAR_QUESTION_PROMPT")
    MISSION1_PROMPT = utils.resource_path("Prompt_helpers/MISSION1_PROMPT_TEST2")
    MISSION2_PROMPT = utils.resource_path("Prompt_helpers/MISSION2_PROMPT_4")
    FIXER1 = """Last time I gave you the following prompt:\n{MAIN_PROMPT}\nYou returned:\n{RESPONSE}
    I got this massage while trying to find the tables:\n{E}\n.
    try to fix your answer so it will 100% work(also if needed check that all tables exist in the tables given to you).
    You should return with the same format, giving a reasoning for the rest of the code. 
    You should act in your reasoning like you never made a mistake in the first place.
    Meaning that in <reasoning> you only explain what information you decided to give, and in <errorhandling> you explain what changes you made for the code for that to work.
    Remember to adjust the tablenames if needed."""
    FIXER2 = """Last time I gave you the following prompt:\n{MAIN_PROMPT}\nYou returned:\n{RESPONSE}
    I got this massage while trying to run code {I}:\n{E}\n Now in your answer, try to fix the code but be 100% it will work (also look at codes after {I} and check them).
    You should return with the same format, giving a reasoning for the rest of the code. 
    You should act in your reasoning like you never made a mistake in the first place.
    Meaning that in <reasoning> you only explain what information you decided to give, and in <errorhandling> you explain what changes you made for the code for that to work.
    Remember to adjust the tablenames if needed aswell. """

    def __init__(self, tries=2):
        """
        Initialize the NLtoSQL instance.

        Args:
            tries (int): The number of attempts to make when generating SQL queries.
        """
        self.__claude_client = anthropic.Anthropic()
        self.__cur_connection = None
        self.__tables_dict = None
        self.__tries = tries
        self.question_db = QuestionDatabase()
        with open(NLtoSQL.MISSION1_PROMPT, 'r') as file:
            self.__prompt1 = file.read()
        with open(NLtoSQL.MISSION2_PROMPT, 'r') as file:
            self.__prompt2 = file.read()
        with open(NLtoSQL.SIMILAR_QUESTION_PROMPT, 'r') as file:
            self.__similar_question_prompt = file.read()

    def save_question(self, question, sql_code):
        self.question_db.add_question(question, sql_code)
        nice_print("Question and SQL code saved for future reference.")

    def is_connected_to_server(self):
        """
        Check if the instance is connected to a SQL server.

        Returns:
            bool: True if connected, False otherwise.
        """
        return False if self.__cur_connection is None else True

    def connect_to_server(self, connection):
        """
        Connect to a SQL server and retrieve table information.

        Args:
            connection: A database connection object.
        """
        self.__cur_connection = connection
        self.__tables_dict = self.__get_tables()

    def apply(self, question):
        """
        Process a natural language question and generate SQL queries.

        This method interprets the question, identifies relevant tables,
        generates SQL queries, and executes them to retrieve data.

        Args:
            question (str): The natural language question to process.

        Returns:
            tuple: A tuple containing the SQL code, retrieved data and whether the answer was in the database or not.
                   Returns None if an error was found.
        """
        similar_question = self.__find_similar_question(question)
        if similar_question != "No similar question found.":
            nice_print(f"I found a similar question in the database: '{similar_question}'")
            user_approval = input("Is this the same as your question? (y/n): ").lower()
            if user_approval == 'y':
                sql_code = self.question_db.get_sql_for_question(similar_question)
                if sql_code:
                    nice_print("Using the saved SQL code for this question.")
                    return sql_code, self.__execute_sql(sql_code)[0], True
            else:
                nice_print(f"Proceeding as usual, please wait while I am getting the information.")
        prompt = self.__prompt1.format(QUESTION=question, TABLE_LIST=str(self.__tables_dict.keys()))
        main_prompt = prompt
        for i in range(self.__tries):
            try:
                table_picker_message = self.__claude_client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=1500,
                    temperature=0,
                    system="You are an AI assistant tasked with analyzing a user's question about a database,"
                           " determining its validity, and identifying relevant tables if the question is valid.",
                    messages=[
                        {"role": "user", "content": [{"type": "text", "text": prompt}]}
                    ]
                ).content[0].text
                if "<error>" in table_picker_message:
                    nice_print('\n' + get_tags_info(table_picker_message, tag="error") + '\n')
                    return None, None, None
                table_picker_reasoning = get_tags_info(table_picker_message, tag="reasoning")
                tables = get_tags_info(table_picker_message, tag="tables").strip('][ ').split(',')
                tables_info = [{tables[i].strip("' "): self.__tables_dict[tables[i].strip("' ")]} for i in
                               range(len(tables))]
                break
            except Exception as e:
                prompt = NLtoSQL.FIXER1.format(MAIN_PROMPT=main_prompt, RESPONSE=table_picker_message, E=e)
        prompt = self.__prompt2.format(QUESTION=question, TABLE_INFO=str(tables_info), REASONING=table_picker_reasoning)
        main_prompt = prompt
        for i in range(self.__tries):
            coder_response = self.__claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4000,
                temperature=0,
                system="You are a microsoft SQL coder, please be sure that the code you generate works on microsoft SQL",
                messages=[
                    {"role": "user", "content": [{"type": "text", "text": prompt}]
                     }
                ]
            ).content[0].text
            if "<error>" in coder_response:
                nice_print('\n' + get_tags_info(coder_response, tag="error") + '\n')
                return None, None, None
            columns_reasoning = get_tags_info(coder_response, tag="user_reasoning")
            SQLcodes = list(zip(get_tags_info(coder_response, tag="code").strip('][ ').split('##D##'),
                                get_tags_info(coder_response, tag="tablename").strip('][ ').split(',')))
            data_tables = self.__execute_sql(SQLcodes)
            if data_tables[1]:
                nice_print("Missions succeeded.\n")
                nice_print("Data extracted:\n" + columns_reasoning + '\n')
                return SQLcodes, data_tables[0], False
            else:
                prompt = NLtoSQL.FIXER2.format(MAIN_PROMPT=main_prompt, RESPONSE=coder_response,
                                               I=data_tables[0][0], E=data_tables[0][1])
        return None, None, None

    def __get_tables(self):
        """
        Retrieve table and column information from the connected database.

        Returns:
            dict: A dictionary mapping table names to lists of column names.
        """

        try:
            with self.__cur_connection.cursor() as cursor:
                # Get all tables and their columns
                sql = """
                        SELECT 
                            t.TABLE_NAME, 
                            c.COLUMN_NAME
                        FROM 
                            INFORMATION_SCHEMA.TABLES t
                        JOIN 
                            INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
                        WHERE 
                            t.TABLE_SCHEMA = SCHEMA_NAME()
                        """
                cursor.execute(sql)
                result_set = cursor.fetchall()

                table_dict = {table: [] for table in NLtoSQL.ESSENTIAL_TABLES}
                for table_name, column_name in result_set:
                    if table_name in table_dict:
                        table_dict[table_name].append(column_name)
                    else:
                        table_dict[table_name] = [column_name]

            return table_dict
        except Exception as e:
            print("There was a problem connecting to the SQL database, please be sure the information is right")
            print(e)
            return None

    def __find_similar_question(self, question):
        prompt = self.__similar_question_prompt.format(
            QUESTION=question,
            QUESTION_LIST="\n".join(f"- {q}" for q in self.question_db.get_questions().keys())
        )

        response = self.__claude_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=100,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    def __execute_sql(self, sql_code):
        try:
            cursor = self.__cur_connection.cursor()
            data_tables = []
            j = 0
            while j < len(sql_code):
                cursor.execute(sql_code[j][0])
                final_result = utils.fix_decimal_values(cursor.fetchall())
                headers = [cursor.description[i][0] for i in range(len(cursor.description))]
                final_result_data = [[item for item in sublist] for sublist in final_result]
                df = pd.DataFrame(final_result_data, columns=headers)
                data_tables.append((sql_code[j][1].strip(), df))
                j += 1
            return data_tables, True
        except Exception as e:
            return (j,e), False
