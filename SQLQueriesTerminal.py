from GptPrompetTest import NLtoSQL
import pyodbc

server = 'DESKTOP-23IMM3A\\SQLEXPRESS'
database = 'GDB_01_TEST'
username = 'sa'
pwd = 'sa'

if __name__ == '__main__':
    connection = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' +
        server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + pwd + ';')
    question = input("Welcome to the SQL data retriever,\n"
                     "please ask questions regrading the corresponding dataset, (at anytime type 'exit' or 'quit' to quit):\n")
    while True:
        if question.lower() in ['exit', 'quit', 'no']:
            break
        NLtoSQL(question, connection)
        question = input("Do you have any additional requests?\n")

    connection.close()