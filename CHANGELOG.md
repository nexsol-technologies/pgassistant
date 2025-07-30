# Change Log

## [1.9.6] - 2025-07-30

### Features
- A new blog built with Hugo is now available for pgAssistant. It covers usage tips, performance advice, and deployment best practices. [Check it out](https://beh74.github.io/pgassistant-blog/). 
    - Source code is [here](https://github.com/beh74/pgassistant-blog/tree/main/content). Everyone is welcome to contribute!
    - The site is automatically deployed to GitHub Pages using a GitHub Actions workflow. Any push to the main branch triggers a rebuild and redeploy. 
    - Work in progress !
- Prefix all queries performed by pgAssistant with : /* launched by pgAssistant */ 
- Optimizing the issue "Indexe missing on foreign keys" by giving recommandations, depending on the size of the referenced table [documentation here](https://beh74.github.io/pgassistant-blog/doc/issue_index_fk/).
- Experimental : Add a vacuum query to try to optimize the default vacuum parameters for each table. See : [documentation here](https://beh74.github.io/pgassistant-blog/post/vaccum/)


## [1.9.5] - 2025-07-20

### Features
- Add top 5 clients on dashboard
- Add issues on dashboard
- Add max connections on dashboard
- Trying to improve the Dashboard UI 

## [1.9.4] - 2025-07-18

### Bug Fixes
- Top 50 queries were not working correctly with PostgreSQL v17

### Features
- Removed unnecessary SQL code from `pg_dump` output
- Refactored LLM response rendering in HTML5 with code copy functionality

## [1.9.3] - 2025-07-14
### Bug Fixes
- On very simple queries, Sqlglot cannot determine which table a column corresponds to
- Some sql queries cause sqlglot to crash during parsing (mainly when using DATE expressions)

## [1.9.2] - 2025-07-12
### Bug Fixes
- Parenthesis are not well interpreted when analyzing a query
- Upgrade node-sass package : security advisor
### Features
- Add a new form to edit [LLM settings](media/llm_settings.png) (URI, models and api key)

## [1.9.1] - 2025-06-30
- Upgrading to alpine 3.22
- Code comments


## [1.9] - 2025-02-28
### Features
- Analyze query, analyze parameter query with sqlglot : gives good results now.
- Analyze query, use pg_stats to get the most common values of a given parameter. See sample [here](media/analyze_parameters.png)
- Analyze query, get the indexe coverage of each table and column of the query. See sample [here](media/index_coverage.png)
- On dashboard, add a link on Hit Cache Ratio zooming on cache usage by table. Quick access on top queries with low usage of cache / index cache. See sample [here](media/cache_usage.png)
- On table menu, add Statistics of table columns
- Round some metrics on top queries
### Bug Fixes
- Remove not necessary javascript librairies

## [1.8] - 2025-02-15
### Features
- Help dev to find a primary key. See a sample result here on [primary key issues](media/issue_missing_pk.png);
- For each table and schema, ask the LLM if the table definitions comply with relevant RFC(s). See sample [here](media/table_structure.png)
- Somebody notice that on foreign keys issues (missing indexes), the suggest query did not use the CREATE INDEX **CONCURRENTLY**. pgAssistant should be used BEFORE to get in production, but a quick copy/paste maybe dangerous. 
### Bug Fixes
- With postgresql v17, pgTune is not working

## [1.7.2] - 2025-02-13
### Features
- Enable pg_stat_statment at connexion.
- Some LLM seams to forget that primary keys are always indexed. Changing the LLM prompt to fix that. 
### Bug Fixes
- Fix issues/7
- Fix issues/5 (I hope so)

## [1.7.1] - 2025-02-07
### Features
- Add comments on EXPLAIN ANALYZE to help dev understand the output of an EXPLAIN ANALYZE result.
- In the statistics view, add columns involved in the queries and operation types. Next step in v1.8: check if indexes exist on these columns (goal: recommend missing indexes to optimize queries).
### Bug Fixes
- Top queries bug with postgresql 17 : pg_stat_statements missing columns with this version
- Upgrade base docker image to get the latest postgresql client : v17.  
- Filter queries that can not be used in an EXPLAIN ANALYZE query 

## [1.7] - 2025-01-26
### Features
- On analyze query, try to identify data type of a parameter. Try to get 10 values of this parameter to help the user provide parameters
- Use sql-formatter to format SQL
- Adding an issue query : find foreign keys with wrong data type
- Adding autovacuum=on to docker-compose parameter
### Bug Fixes
- When a query has more than 9 parameters, parameter replacement fails.

---

## [1.6] - 2025-01-24
### Features
- Run Pg Assistant recommandations on database
### Bug Fixes
- Missing indexes on FK.

---

## [1.5.1] - 2024-12-15
### Features
- Optimize LLM queries
- Optimize gunicorn configuration.

---

## [1.5] - 2024-12-08
### Features
- Enabled support for **local LLMs** like **Ollama**.
- Enhanced LLM prompts with **Markdown formatting**.

### Documentation
- Add specific documentation for **LLM usage**.

---

## [1.4] - 2024-12-06
### Features
- Added **table statistics** display.
- Introduced **ranked queries** functionality.


---

## [1.3] - 2024-11-29
### Features
- Introduced the ability to use **DDL** to query LLMs.
- Improved LLM responses with **Markdown formatting**.

### Optimization
- Optimized the Docker image.

---

## [1.2-1] - 2024-08-18
### Features
- Added loading spinners for better user feedback.

### Bug Fixes
- Fixed dashboard bug for PostgreSQL versions < 14 (conflict counting issue).

---

## [1.2] - 2024-08-14
### Features
- Implemented **Bootstrap Data Tables** for enhanced UI.
- Added estimated rows count to the dashboard.

---

## [1.1] - 2024-08-11
### Features
- Added a menu to browse all queries in `myqueries.json`.
- Integrated **pgTune** for PostgreSQL tuning ([pgTune](https://pgtune.leopard.in.ua/)).


## [1.0.0] - 2024-08-04
- **Initial Release**: Repository initialized!









