# Change Log

## [1.0.0] - 2024-08-04
- **Initial Release**: Repository initialized!

---

## [1.1] - 2024-08-11
### Features
- Added a menu to browse all queries in `myqueries.json`.
- Integrated **pgTune** for PostgreSQL tuning ([pgTune](https://pgtune.leopard.in.ua/)).

---

## [1.2] - 2024-08-14
### Features
- Implemented **Bootstrap Data Tables** for enhanced UI.
- Added estimated rows count to the dashboard.

---

## [1.2-1] - 2024-08-18
### Features
- Added loading spinners for better user feedback.

### Bug Fixes
- Fixed dashboard bug for PostgreSQL versions < 14 (conflict counting issue).

---

## [1.3] - 2024-11-29
### Features
- Introduced the ability to use **DDL** to query LLMs.
- Improved LLM responses with **Markdown formatting**.

### Optimization
- Optimized the Docker image.

---

## [1.4] - 2024-12-06
### Features
- Added **table statistics** display.
- Introduced **ranked queries** functionality.

---

## [1.5] - 2024-12-08
### Features
- Enabled support for **local LLMs** like **Ollama**.
- Enhanced LLM prompts with **Markdown formatting**.

### Documentation
- Add specific documentation for **LLM usage**.

---

## [1.5.1] - 2024-12-15
### Features
- Optimize LLM queries
- Optimize gunicorn configuration.

---

## [1.6] - 2025-01-24
### Features
- Run Pg Assistant recommandations on database
### Bug Fixes
- Missing indexes on FK.

## [1.7] - 2025-01-26
### Features
- On analyze query, try to identify data type of a parameter. Try to get 10 values of this parameter to help the user provide parameters
- Use sql-formatter to format SQL
- Adding an issue query : find foreign keys with wrong data type
- Adding autovacuum=on to docker-compose parameter
### Bug Fixes
- When a query has more than 9 parameters, parameter replacement fails.

## [1.7.1] - 2025-02-07
### Features
- Add comments on EXPLAIN ANALYZE to help dev understand the output of an EXPLAIN ANALYZE result.
- In the statistics view, add columns involved in the queries and operation types. Next step in v1.8: check if indexes exist on these columns (goal: recommend missing indexes to optimize queries).
### Bug Fixes
- Top queries bug with postgresql 17 : pg_stat_statements missing columns with this version
- Upgrade base docker image to get the latest postgresql client : v17.  
- Filter queries that can not be used in an EXPLAIN ANALYZE query 