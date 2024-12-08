import subprocess
import re
from pygments import highlight
from pygments.lexers import SqlLexer
from pygments.formatters import HtmlFormatter

def sql_to_html(sql_query):
    """
    Convert a SQL query into syntax-highlighted HTML.

    Args:
        sql_query (str): The SQL query to format.

    Returns:
        str: HTML code with syntax highlighting.
    """
    # Use the SQL lexer and an HTML formatter
    formatter = HtmlFormatter(style="colorful", full=True, linenos=False)
    highlighted_sql = highlight(sql_query, SqlLexer(), formatter)
    return highlighted_sql

def remove_pg_catalog_lines(sql_script):
    """
    Remove all lines starting with 'SELECT pg_catalog.' from the SQL script.

    Args:
        sql_script (str): The input SQL script.

    Returns:
        str: The cleaned SQL script.
    """
    # Use a regular expression to remove lines starting with 'SELECT pg_catalog.'
    cleaned_script = re.sub(r'^SELECT pg_catalog\..*$', '', sql_script, flags=re.MULTILINE)
    return cleaned_script.strip()

def generate_tables_ddl(host, port, database, user, password, tables):
    """
    Generate a DDL for the tables in parameter using pg_dump.
    """    
    try:
        # Build the `--table` arguments for pg_dump
        table_args = " ".join([f"--table {table}" for table in tables])

        # Combine the command with piping
        command = f"""
        PGPASSWORD="{password}" pg_dump -h {host} -p {port} -U {user} -d {database} --schema-only {table_args} |
        sed -e '/^--/d' |
        sed -e '/^SET/d' 
        """

        # Run the command in a shell
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            text=True,
            shell=True,
            check=True
        )
        ddl_s = result.stdout.replace("\n\n", "\n")
        return remove_pg_catalog_lines(ddl_s)
    
    except subprocess.CalledProcessError as e:
        print(f"Error generating DDL: {e}")
        return None
