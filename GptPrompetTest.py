# Import the required packages
import openai
import json
import pyodbc
from tabulate import tabulate
prompt_helper = """If you need some table columns return answer in only one format:
 [TABLE_NAME1, TABLE_NAME2, TABLE_NAME3, ...]. And if the questions you got doesn't look like an sql task return "not good"
 """

API_KEY = 'sk-proj-tMMXyFQZiVRwuFmHpMF2T3BlbkFJ92I0T3GniB4z78vVoEIF'
MISSION1 = """You are a microsoft SQL preprocess agent, given a question and tables you choose the most relevant tables for 
the question (you can choose up to 5 tables) and you return answer in only one format:
 [TABLE_NAME1, TABLE_NAME2, TABLE_NAME3, ...]"""

MISSION2 = """You are a microsoft SQL agent, users asks you to retrieve information from sql tables.
             Given tables and their columns you generate a SQL code according to the task, or return "task isn't valid"
             if there is nothing similar in the tables or columns. Important When you write sql
             code you check if the columns you choose are indeed from the table.
             You can return only the code without markdown notation and unless stated otherwise retrieve only 20 rows and limit
             yourself to six most important columns.
             some examples for microsoft SQL code are:
             
             SELECT COL1, COL2, COL3, COL4, COL5, COL6
             FROM TABLE;
             
             SELECT TOP (1000) [DOC_NO]
              ,[ENTRY_DOC_NO]
              ,[PARTNUMBER]
              ,[DESCRIPTN]
              ,[MODEL_USAGE]
              ,[COND]
              ,[UNITP]
              ,[QTY_UM]
              ,[PUBLISHED_DATE]
              ,[PUBLISHED_DATE_SPECIFIED]
              ,[VENDOR_MFG_NAME]
              ,[RECLOCK]
              ,[ADDED_USR]
              ,[ADDED_DTE]
              ,[UPDATED_USR]
              ,[UPDATED_DTE]
               FROM TABLE;
             """
# Data information
server = 'DESKTOP-23IMM3A\\SQLEXPRESS'
database = 'GDB_01_TEST'
username = 'sa'
pwd = 'sa'
openai_api_key = 'sk-proj-tMMXyFQZiVRwuFmHpMF2T3BlbkFJ92I0T3GniB4z78vVoEIF'

# Get information about your data,
# and use it translate natural language to SQL code with OpenAI to then execute it on your data
def NLtoSQL(question, sql_connection):
    response = "There was an error connecting to the server, please try again"
    try:
        # Execute the query to retrieve the column information
        with sql_connection.cursor() as cursor:
            sql = "SELECT TABLE_NAME,COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS"
            cursor.execute(sql)
            result_set = cursor.fetchall()
            # Extract the column names from the cursor description
            column_names = [column[0] for column in cursor.description]
            table_dict = dict()
            for x, y in result_set:
                if (x in table_dict.keys()):
                    table_dict[x].append(y)
                else:
                    table_dict[x] = [y]

            # Format the result set as a JSON string
        # Define the OpenAI prompt
        cl = openai.OpenAI(api_key=API_KEY)
        cc = cl.chat.completions.create(
            messages=[
                {"role": "system", "content": MISSION1},
                {"role": "assistant", "content": "Relevant tables and columns names: " + str(table_dict.keys())},
                {"role": "user", "content": question }
            ], stream=False, max_tokens=420, model="gpt-3.5-turbo", temperature=0)
        response = cc.choices[0].message.content.strip('][ ').split(',')
        tables_info = [{response[i].strip("' "): table_dict[response[i].strip("' ")]} for i in range(len(response))]

        cc = cl.chat.completions.create(
            messages=[
                {"role": "system", "content": MISSION2},
                {"role": "assistant", "content": "Relevant tables and columns names: " + str(tables_info)},
                {"role": "user", "content": question}
            ], stream=False, max_tokens=420, temperature=0, model="gpt-3.5-turbo")
        response = cc.choices[0].message.content.strip("`").split(';')
        print("QUESTION ASKED:\n" + question + "\n")
        for sql_code in response:
            if sql_code:
                cursor.execute(sql_code)
                final_result = cursor.fetchall()
                headers = [cursor.description[i][0] for i in range(len(cursor.description))]
                # Print the question + SQL Query + Generated Response
                print("GENERATED RESULTS:")
                print(tabulate(final_result, headers=headers, tablefmt='psql') +'\n')
                print("SQL CODE USED:\n" + "```\n" + sql_code.strip() + "\n```")

    except Exception as e:
        print("I had problems retrieving the query you have asked for from the database. "
              "Can you be a bit more specific? \nI remind you that my usage is to retrieve "
              "information from SQL databases.")




# Test the function
if __name__ == '__main__':
    connection = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' +
        server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + pwd + ';')

    NLtoSQL("Hello", connection)

