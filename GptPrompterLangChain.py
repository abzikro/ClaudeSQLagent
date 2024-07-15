import pyodbc
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_openai import OpenAI
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI
import json

OPENAI_API_KEY = 'sk-proj-tMMXyFQZiVRwuFmHpMF2T3BlbkFJ92I0T3GniB4z78vVoEIF'
DB_USER='sa'
DB_PASSWORD='sa'
DB_HOST='DESKTOP-23IMM3A\\SQLEXPRESS'
DB_NAME='GDB_01_TEST'
DB_DICT_NAME='DataDictionary_2008R2'

if __name__ == '__main__':

    # connection = pyodbc.connect(
    #     'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + DB_HOST + ';DATABASE=' +
    #     DB_DICT_NAME + ';UID=' + DB_USER + ';PWD=' + DB_PASSWORD + ';')
    # cursor = connection.cursor()
    # sql = "SELECT TABLE_NAME,COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS"
    # cursor.execute(sql)
    # result_set = cursor.fetchall()
    #
    # # Extract the column names from the cursor description
    # column_names = [column[0] for column in cursor.description]
    #
    # # Extract the column names from each row and convert to dictionary
    # result_list = [dict(zip(column_names, row)) for row in result_set]
    #
    # # Format the result set as a JSON string
    # result_set_json = json.dumps(result_list)
    #
    db_url = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
    db = SQLDatabase.from_uri(
        database_uri=db_url
    )

    toolkit = SQLDatabaseToolkit(db=db, llm=OpenAI(temperature=0, openai_api_key=OPENAI_API_KEY,  max_tokens=1000))

    sql_agent = create_sql_agent(
        llm=ChatOpenAI(temperature=0, model="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY,  max_tokens=1000),
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    )
    sql_agent.handle_parsing_errors = True
    try:
        sql_mission = "Can you provide me information about our bank contacts?"
        # Please
        # try to understand first if this is an SQL query, "
        # "else just answer some informative knowledge about your mission."
        # "If there is not a similiar table name tell the user that the query he have asked for is not valid"
        # " to extract from the database and ask them to be a bit more specific?"
        # "This is your SQL retrieval mission:
        prompt = (f"{sql_mission}\n")
        response = sql_agent.invoke(prompt)
        print(response['output'])
    except Exception as e:
        print("The query you have asked is not possible to extract from the database. Can you be a bit more specific?")