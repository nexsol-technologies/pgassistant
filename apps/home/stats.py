

def add_or_update_table_info(tables_info, table_name, query_count, avg_execution_time, rows, operation_type):
    # Vérifie si la table existe déjà dans la liste
    for table_info in tables_info:
        if table_info["table_name"] == table_name:
            # Met à jour les informations existantes
            table_info["query_count"] += query_count
            table_info["rows"] += rows
            # Calcul d'un nouveau temps moyen pondéré
            total_queries = table_info["query_count"]
            table_info["avg_execution_time"] = (
                (table_info["avg_execution_time"] * (total_queries - query_count)) + (avg_execution_time * query_count)
            ) / total_queries
            table_info["operation_type"] = operation_type
            return
    
    # Si la table n'existe pas, ajoute une nouvelle entrée
    new_table_info = {
        "table_name": table_name,
        "query_count": query_count,
        "avg_execution_time": avg_execution_time,
        "rows": rows,
        "operation_type": operation_type
    }
    tables_info.append(new_table_info)
