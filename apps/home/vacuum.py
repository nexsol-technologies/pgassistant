ALTER_VACUUM_ON="SET autovacuum TO 'on';"
VACUUM_OPTIMIZED="""
DO $$
DECLARE
    tbl RECORD;
    live_tuples BIGINT;
    dead_tuples BIGINT;
    default_vacuum_threshold INTEGER;
    default_vacuum_scale_factor NUMERIC;
    default_analyze_threshold INTEGER;
    default_analyze_scale_factor NUMERIC;
    vacuum_threshold INTEGER;
    vacuum_scale_factor NUMERIC;
    analyze_threshold INTEGER;
    analyze_scale_factor NUMERIC;
    table_size NUMERIC;
    current_vacuum_threshold INTEGER;
    current_vacuum_scale_factor NUMERIC;
    current_analyze_threshold INTEGER;
    current_analyze_scale_factor NUMERIC;
    reloptions TEXT[];
BEGIN
    -- Obtenir les paramètres par défaut de la base
    SELECT 
        current_setting('autovacuum_vacuum_threshold')::INTEGER INTO default_vacuum_threshold;
    SELECT 
        current_setting('autovacuum_vacuum_scale_factor')::NUMERIC INTO default_vacuum_scale_factor;
    SELECT 
        current_setting('autovacuum_analyze_threshold')::INTEGER INTO default_analyze_threshold;
    SELECT 
        current_setting('autovacuum_analyze_scale_factor')::NUMERIC INTO default_analyze_scale_factor;

    -- Parcourir toutes les tables utilisateur
    FOR tbl IN
        SELECT
            st.schemaname,
            st.relname,
            st.n_live_tup,
            st.n_dead_tup,
            pg_total_relation_size(st.relid) AS total_size,
            c.reloptions
        FROM
            pg_stat_user_tables st
        JOIN
            pg_class c ON st.relid = c.oid
        WHERE
            st.n_live_tup > 0 -- Filtrer les tables avec des tuples vivants
    LOOP
        live_tuples := tbl.n_live_tup;
        dead_tuples := tbl.n_dead_tup;
        table_size := tbl.total_size;
        reloptions := tbl.reloptions;

        -- Calculer des paramètres adaptés pour cette table
        vacuum_threshold := default_vacuum_threshold;
        vacuum_scale_factor := default_vacuum_scale_factor;
        analyze_threshold := default_analyze_threshold;
        analyze_scale_factor := default_analyze_scale_factor;

        -- Adapter les paramètres en fonction des caractéristiques de la table
        IF live_tuples > 1000000 THEN
            vacuum_scale_factor := 0.02; -- Plus agressif pour les grandes tables
            analyze_scale_factor := 0.01;
        ELSIF live_tuples > 100000 THEN
            vacuum_scale_factor := 0.05; -- Moyennement agressif
            analyze_scale_factor := 0.02;
        END IF;

        -- Adapter les seuils pour les petites tables
        IF live_tuples < 10000 THEN
            vacuum_threshold := GREATEST(default_vacuum_threshold, 100);
            analyze_threshold := GREATEST(default_analyze_threshold, 100);
        END IF;

        -- Vérifier les paramètres actuellement appliqués à la table
        SELECT
            (SELECT unnest(regexp_matches(array_to_string(reloptions, ','), 'autovacuum_vacuum_threshold=(\d+)', 'g'))::INTEGER LIMIT 1)
            INTO current_vacuum_threshold;
        SELECT
            (SELECT unnest(regexp_matches(array_to_string(reloptions, ','), 'autovacuum_vacuum_scale_factor=([\d.]+)', 'g'))::NUMERIC LIMIT 1)
            INTO current_vacuum_scale_factor;
        SELECT
            (SELECT unnest(regexp_matches(array_to_string(reloptions, ','), 'autovacuum_analyze_threshold=(\d+)', 'g'))::INTEGER LIMIT 1)
            INTO current_analyze_threshold;
        SELECT
            (SELECT unnest(regexp_matches(array_to_string(reloptions, ','), 'autovacuum_analyze_scale_factor=([\d.]+)', 'g'))::NUMERIC LIMIT 1)
            INTO current_analyze_scale_factor;

        -- Utiliser les valeurs par défaut si aucun paramètre spécifique n'est défini
        current_vacuum_threshold := COALESCE(current_vacuum_threshold, default_vacuum_threshold);
        current_vacuum_scale_factor := COALESCE(current_vacuum_scale_factor, default_vacuum_scale_factor);
        current_analyze_threshold := COALESCE(current_analyze_threshold, default_analyze_threshold);
        current_analyze_scale_factor := COALESCE(current_analyze_scale_factor, default_analyze_scale_factor);

        -- Générer une commande ALTER TABLE uniquement si les valeurs diffèrent des valeurs actuelles
        IF vacuum_threshold != current_vacuum_threshold
            OR vacuum_scale_factor != current_vacuum_scale_factor
            OR analyze_threshold != current_analyze_threshold
            OR analyze_scale_factor != current_analyze_scale_factor THEN
            RAISE NOTICE 'ALTER TABLE %.% SET (autovacuum_vacuum_threshold = %, autovacuum_vacuum_scale_factor = %, autovacuum_analyze_threshold = %, autovacuum_analyze_scale_factor = %);',
                tbl.schemaname,
                tbl.relname,
                vacuum_threshold,
                vacuum_scale_factor,
                analyze_threshold,
                analyze_scale_factor;
        END IF;
    END LOOP;
END $$;
"""

VACUUM_LAUNCH = """
SELECT 
    schemaname || '.' || relname AS table_name,
    n_live_tup AS live_tuples,
    n_dead_tup,
    n_tup_upd ,
    pg_size_pretty(pg_total_relation_size(relid)) AS table_size,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    CASE 
        WHEN n_dead_tup  + n_tup_upd> 1000 THEN 'VACUUM ANALYZE ' || schemaname || '.' || relname || ';'
        WHEN n_live_tup=0 and last_analyze is null then 'ANALYZE ' || schemaname || '.' || relname || ';'
        WHEN (last_vacuum IS NULL AND last_autovacuum IS null and last_analyze is null) THEN 'VACUUM ANALYZE ' || schemaname || '.' || relname || ';'
        ELSE '-- NOTHING TO DO'
    END AS maintenance_suggestion
FROM 
    pg_stat_user_tables

ORDER BY 
    n_dead_tup DESC, pg_total_relation_size(relid) DESC;

"""

def vacuum_get_tables_to_analyze():
    return None

def vacuum_get_tables_optimized_parameters():
    return VACUUM_OPTIMIZED