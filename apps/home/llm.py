import os
from openai import OpenAI
from .ddl import generate_tables_ddl
from .sqlhelper import get_tables
import markdown
import re

def fix_code_blocks(text):
    # Ajoute un saut de ligne avant chaque bloc ```lang s’il n’y en a pas déjà un
    text = re.sub(r'([^\n])(```\w+)', r'\1\n\2', text)
    return text

def query_chatgpt(question):
    """
    Sends a question to ChatGPT (or a local LLM) and returns the response.

    :param question: The user's question to send to the LLM.
    :return: Formatted Markdown response from the model.
    """    
    api_key=os.environ.get('OPENAI_API_KEY', None)
        
    local_llm=os.environ.get('LOCAL_LLM_URI', None)
    model_llm=os.environ.get('OPENAI_API_MODEL', None)

    if not api_key:
        raise Exception("The environment variable OPENAI_API_KEY is not set. I can't use OpenAPI !")

    # Using local LLM
    if (local_llm):
        client = OpenAI(api_key=api_key, base_url = local_llm)
    # Using OpenAI
    else:
        client = OpenAI(api_key=api_key)

    completion = client.chat.completions.create(
        model=model_llm,
        messages=[
            {"role": "system", "content": "You are a Postgresql database expert"},
            {"role": "user", "content": question }
        ],
        temperature=0.2,
        max_tokens=2000,
        frequency_penalty=0.1,
        presence_penalty=0.6,
        n=1  
    )

    #return(markdown.markdown(completion.choices[0].message.content,extensions=["fenced_code", "codehilite", "extra"]))

    md_text = fix_code_blocks(completion.choices[0].message.content)
    print (f"LLM response: {completion.choices[0].message.content}")

    html = markdown.markdown(
        md_text,
        extensions=["fenced_code", "codehilite", "extra"],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "css_class": "highlight"
            }
        },
        output_format="html5"
    )
    return html

def get_llm_query_for_query_analyze (host, port, database, user, password, sql_query, rows):
    """
    Generates a detailed prompt for an LLM to analyze and optimize a PostgreSQL query.

    :param host: The database host.
    :param port: The database port.
    :param database: The database name.
    :param user: The database user.
    :param password: The database password.
    :param sql_query: The SQL query with `EXPLAIN ANALYZE` prefix.
    :param rows: The output of `EXPLAIN ANALYZE` as a list of dictionaries.
    :return: A formatted string containing query details for LLM analysis.
    """    
    query = sql_query.replace ("EXPLAIN ANALYZE  ", "")
    tables = get_tables(query)
    
    # Generate the DDL (schema) of the involved tables
    ddl = generate_tables_ddl(host, port, database, user, password, tables)

    # Construct the LLM prompt with structured details
    llm = (
        "I have a PostgreSQL query that I would like to optimize. Below, I have provided the necessary details:\n\n"
        f"1. **DDL of the table(s) involved**:\n```sql\n{ddl}\n```\n\n"
        f"2. **The SQL query**:\n```sql\n{sql_query}\n```\n\n"
        "3. **`EXPLAIN ANALYZE` output**:\n\n```"
    )
    llm += "\n".join(row['QUERY PLAN'] for row in rows)
    llm += "\n```\n"
    
    # Add the optimization request
    llm += (
    "\nCould you analyze this query and suggest optimizations? If optimizations are possible, please provide the necessary SQL statements "
    "(e.g., additional indexes or query rewrites) and explain the reasoning behind your recommendations."
    )
    # Add a cautionary note about redundant index recommendations
    llm += (
    "\n\n**Important Notice:** When suggesting optimizations, especially related to indexes, please carefully review the DDL provided above. "
    "Some indexes may already exist, and redundant or unnecessary index recommendations should be avoided. Ensure any suggested indexes align "
    "with the schema and constraints defined in the DDL. Never forget that primary keys are always indexed."
    )
    # Encourage careful and well-supported recommendations
    llm += (
    "\nFeel free to reflect on possible optimizations and reasoning before finalizing your response. Ensure all suggestions are well-supported "
    "and avoid any unnecessary or redundant recommendations."
    )
    return llm

def generate_primary_key_prompt(table_name: str, ddl: str) -> str:
    """
    Generates a prompt for an LLM to determine the best primary key for a PostgreSQL table
    and provide the necessary ALTER TABLE command.

    Args:
        table_name (str): The name of the table.
        ddl (str): The DDL (Data Definition Language) statement for the table.

    Returns:
        str: A formatted prompt for the LLM.
    """
    prompt = f"""
I have a PostgreSQL table that does not have a primary key. In some cases, a natural key (like an ISO country code) is a good choice, 
but when no stable unique column exists, a technical key (`SERIAL` or `UUID`) is preferable.

A technical key is best when:
- No single column or combination of columns is reliably unique.
- Natural keys are too large, unstable, or inefficient for indexing.
- Composite keys make queries and relationships complex.
- The table is large, requiring fast lookups and indexing.
- The system is distributed and needs globally unique identifiers.

Given the following table structure, suggest the most appropriate primary key (either an existing column or a new technical key) and explain why.

Additionally, provide the necessary **ALTER TABLE** SQL command(s) to implement your suggested primary key.

**One more thing** : Can you also check if the column types and their lengths in the following table are appropriate based on their names and potential usage ? Please mention RFC conventions if any exist end provide an ALTER command to change the column data type or length.

**Table Name:** {table_name}  
**DDL:**  
```sql
{ddl}
```
"""
    return prompt

def analyze_table_format (ddl: str) -> str:
    llm_prompt = f"""
# 📌 SQL Table Structure Validation Based on RFC & International Standards (PostgreSQL Compatible)

## **Task**  
You are an expert in **database design**, **SQL optimization**, and **data standards**. Your goal is to **validate the structure of a SQL table (DDL)** based on relevant **RFCs, international standards, and best practices**.  

## **Instructions**  
1. **Analyze the given DDL statement** and verify whether it adheres to **established standards and best practices** in different domains, including:  
   - **Networking & Web** (RFCs for emails, domain names, and addresses)  
   - **Healthcare** (FHIR, HL7)  
   - **E-commerce & Invoicing** (UBL, UN/CEFACT, EDIFACT)  
   - **Finance & Payments** (ISO 20022, IBAN, BIC, SWIFT, PCI-DSS)  
   - **Geolocation** (ISO 3166 for country codes, ISO 6709 for geolocation)  
   - **Personal Data & Identity** (ISO 5218 for gender, ISO 27799 for health privacy, OIDC/SAML for identity management)  
   - **Date & Time** (ISO 8601)  
   - **Languages & Localization** (ISO 639 for language codes, ISO 4217 for currencies)  
   - **Database Best Practices** (Normalization, indexing, constraints)  
2. **Validate column types, sizes, constraints, and indexes**, ensuring compliance with:  
   - **RFC 5322** for **email addresses**  
   - **RFC 6350** for **names and addresses (vCard format)**  
   - **RFC 3696** for **name and domain validation**  
   - **FHIR (HL7 Fast Healthcare Interoperability Resources)** for **medical data**  
   - **UBL (Universal Business Language)** for **invoices and orders**  
   - **ISO 20022** for **financial transactions**  
   - **ISO 3166** for **country codes**  
   - **ISO 5218** for **gender classification**  
   - **ISO 4217** for **currency codes**  
   - **ISO 8601** for **date and time formats**  
   - **E.164** for **phone number formatting**  
3. **Propose improvements**:  
   - Adjust **column data types or sizes** if necessary  
   - Add missing **constraints** (e.g., `NOT NULL`, `UNIQUE`, `CHECK`)  
   - Optimize **indexing strategies** for better performance  
4. **Generate SQL `ALTER TABLE` statements**, ensuring **100% PostgreSQL compatibility**:  
   - **Use PostgreSQL syntax for altering column types** (`ALTER COLUMN ... SET DATA TYPE`)  
   - **Use `ADD CONSTRAINT ... CHECK(...)` for validations**  
   - **Use `CREATE INDEX` to improve search performance**  
5. **Provide justifications** for each recommended change based on relevant standards.  

---

## **Here is the DDL to analyze**  
```sql
{ddl}
```
"""
    return llm_prompt


def get_llm_query_for_query_optimize (sql_query):
    llm = (
        "Could you optimize this postgresql query for me : \n "
        f"{sql_query}\n"
    )
    return llm

def list_available_models():
    """
    Returns a list of available models from the OpenAI API or a compatible API (like Ollama).
    - Uses OPENAI_API_KEY if available.
    - Otherwise, uses LOCAL_LLM_URI with a dummy 'none' API key.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LOCAL_LLM_URI")

    if not api_key and not base_url:
        raise ValueError("Neither OPENAI_API_KEY nor LOCAL_LLM_URI is set.")

    # Initialize the OpenAI client
    client = OpenAI(
        api_key=api_key or "none",  # "none" works for Ollama or APIs without authentication
        base_url=base_url or "https://api.openai.com/v1"
    )

    try:
        models = client.models.list()
        return [model.id for model in models.data]
    except Exception as e:
        print(f"❌ Error fetching models: {e}")
        return []