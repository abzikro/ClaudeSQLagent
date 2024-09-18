# SQL Data Retriever

## Overview

SQL Data Retriever is an advanced application that allows users to query SQL databases using natural language. It leverages the power of AI to interpret user questions, generate appropriate SQL queries, and retrieve relevant data from the database. This tool bridges the gap between non-technical users and complex database structures, making data retrieval more accessible and user-friendly.

## Features

- Natural Language Processing: Converts user questions into SQL queries
- AI-Powered Table Selection: Identifies relevant tables based on the user's question
- Dynamic SQL Generation: Creates optimized SQL queries to answer user questions
- Similar Question Detection: Identifies and suggests previously answered similar questions
- Artifact Creation: Generates visualizations and saves query results
- Encrypted Storage: Securely stores connection information and API keys

## Components

1. **Terminal.py**: The main interface for user interaction
2. **NLtoSQL.py**: Core logic for converting natural language to SQL queries
3. **QuestionDatabase.py**: Manages a database of previously answered questions
4. **utils.py**: Utility functions for various operations

## Requirements

- Python 3.x
- Required Python packages: 
  - pyodbc
  - pandas
  - anthropic
  - cryptography
  - tabulate

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/abzikro/PentagonSQLproject.git
   ```
2. Install the required dependencies:
   ```
   pip install -r requirements.txt

3. Ensure you have the necessary ODBC drivers installed for your SQL server.

4. Set up your Claude API key from Anthropic.

## Usage

1. Run the `Terminal.py` script:
   ```
   python Terminal.py
   ```

2. Follow the prompts to set up your database connection and Claude API key.

3. Once connected, you can start asking questions about your database in natural language.

4. The system will interpret your question, generate SQL queries, and return the relevant data.

5. You can save query results as needed.

## How It Works

1. **User Input**: The user enters a natural language question about the database.

2. **Similar Question Check**: The system checks if a similar question has been asked before.

3. **Table Selection**: AI analyzes the question and selects relevant tables from the database.

4. **SQL Generation**: Based on the selected tables and the question, AI generates optimized SQL queries.

5. **Query Execution**: The system executes the generated SQL queries on the connected database.

6. **Result Presentation**: Query results are presented to the user, with options for saving.

## Security

- Database connection information and API keys are encrypted and stored securely.
- The system uses Windows Authentication or username/password for database connections.

## Limitations

- The accuracy of the SQL generation depends on the AI model's understanding of the question and database structure.
- Complex queries or very specific data requirements may require manual SQL writing.

## Troubleshooting

- If you encounter connection issues, ensure your database credentials and server information are correct.
- For API-related issues, verify that your Claude API key is valid and properly set up.

## Contributing

Contributions to improve the SQL Data Retriever are welcome. Please submit pull requests or open issues on the project repository.

## License

License isn't needed for now.

## Acknowledgments

- This project uses the Claude AI model from Anthropic for natural language processing.
- Thanks to all the open-source libraries that made this project possible.
