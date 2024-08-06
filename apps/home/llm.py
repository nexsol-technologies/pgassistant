from openai import OpenAI
import os

def query_chatgpt(question):
    api_key=os.environ.get('OPENAI_API_KEY', None)
    project=os.environ.get('OPENAI_API_PROJECT', None)

    if not api_key:
        raise Exception("The environment variable OPENAI_API_KEY is not set. I can't use OpenAPI !")

    client = OpenAI(api_key=api_key, project=project)
    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a Postgresql database expert"},
        {"role": "user", "content": question }
    ]
    )
    return(completion.choices[0].message.content)

def get_llm_query_for_query_analyze (sql_query, rows):
    llm = (
        "Could you summarize for me this Postgresql query plan (I don’t want the details) "
        "and tell me if an optimization is required:\n"
        f"The query is : {sql_query}\n"
        "The result is : \n"
    )
    llm += "\n".join(row['QUERY PLAN'] for row in rows)
    llm += "\n"
    return llm

def get_llm_query_for_query_optimize (sql_query):
    llm = (
        "Could you optimize this postgresql query for me : \n "
        f"{sql_query}\n"
    )
    return llm