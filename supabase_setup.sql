-- =============================================================================
-- PropertyScout — Supabase Setup SQL
-- Run these statements in the Supabase SQL Editor
-- (Project → SQL Editor → New query)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Reference table: Puerto Rico municipalities
--    Run this FIRST, then import PR_Municipios via Table Editor → Import CSV
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS municipios (
  name   TEXT PRIMARY KEY,
  region TEXT NOT NULL
);

-- After creating the table, go to:
--   Table Editor → municipios → Import data → upload PR_Municipios (rename to .csv first)


-- ---------------------------------------------------------------------------
-- 2. Enriched view: normalised + derived columns from the properties table
--    Query the dashboard against this view, NOT the raw properties table.
--    Run: DROP VIEW IF EXISTS properties_enriched; before re-running this.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW properties_enriched AS
SELECT
  p.id,
  p.property_id,
  p.title,
  p.price,
  p.pueblo,
  p.link,
  p.piclink,
  p.broker,
  p.assigned_agent,

  -- Date tracking columns
  p.first_seen,
  p.last_seen,
  p.times_seen,
  EXTRACT(YEAR FROM p.last_seen)::INTEGER                           AS last_seen_year,

  -- Price change tracking
  p.price_changed,
  p.previous_price,
  CASE
    WHEN p.price_changed AND p.previous_price IS NOT NULL
    THEN ROUND(((p.price - p.previous_price) / p.previous_price * 100)::NUMERIC, 1)
    ELSE NULL
  END                                                               AS price_change_pct,

  -- Trim whitespace from region
  TRIM(p.region)                                                    AS region_clean,

  -- Split type column into base category + listing status
  CASE
    WHEN p.type LIKE '% New'  THEN TRIM(REPLACE(p.type, ' New',  ''))
    WHEN p.type LIKE '% Repo' THEN TRIM(REPLACE(p.type, ' Repo', ''))
    ELSE TRIM(p.type)
  END                                                               AS base_type,

  CASE
    WHEN p.type LIKE '% New'  THEN 'new_construction'
    WHEN p.type LIKE '% Repo' THEN 'repo'
    ELSE 'standard'
  END                                                               AS listing_status,

  -- Split barrio into neighbourhood type prefix and actual name
  SPLIT_PART(p.barrio, '-', 1)                                      AS barrio_prefix,
  TRIM(
    SUBSTRING(p.barrio FROM POSITION('-' IN p.barrio) + 1)
  )                                                                  AS barrio_name,

  -- Normalise bedrooms to integer (handles ">= 6" and ">=6" variants)
  CASE
    WHEN TRIM(p.bedrooms) IN ('>=6', '>= 6') THEN 6
    WHEN TRIM(p.bedrooms) ~ '^\d+$'          THEN CAST(TRIM(p.bedrooms) AS INTEGER)
    ELSE NULL
  END                                                               AS bedrooms_int,

  -- Normalise bathrooms to integer
  CASE
    WHEN TRIM(p.bathrooms) IN ('>=6', '>= 6') THEN 6
    WHEN TRIM(p.bathrooms) ~ '^\d+$'           THEN CAST(TRIM(p.bathrooms) AS INTEGER)
    ELSE NULL
  END                                                               AS bathrooms_int,

  -- Semantic convenience flags
  (p.broker = 'No Broker')  AS is_fsbo,
  p.optioned                AS is_optioned,

  -- Days on market (first_seen → last_seen spread)
  (p.last_seen - p.first_seen)                                      AS days_tracked

FROM properties p;


-- ---------------------------------------------------------------------------
-- 3. Row Level Security — REQUIRED for the public anon/publishable key to read data
--    Without a read policy on `properties`, the anon key returns ZERO rows (no
--    error), which surfaces in the dashboard as
--    "No listings found for the selected filters."
--
--    Why `properties` and not `properties_enriched`?  The dashboard reads the
--    `properties_enriched` VIEW, but a view stores no data — it reads the
--    underlying `properties` TABLE at query time, and RLS policies attach to
--    tables, not views.  With `security_invoker = on` the view runs as the
--    caller (anon), so the policy on `properties` is what governs access.
--    The service_role key bypasses RLS, so this gap is invisible if you ever
--    test locally with that key.
--    Run this block in the Supabase SQL Editor.
-- ---------------------------------------------------------------------------

-- Make the view run with the *caller's* privileges so the policy below applies
-- to it (and to silence Supabase's "security definer view" linter warning).
ALTER VIEW properties_enriched SET (security_invoker = on);

-- properties: enable RLS + allow public (read-only) SELECT  ← fixes "No listings found"
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read access" ON properties;
CREATE POLICY "Public read access" ON properties
  FOR SELECT
  TO anon, authenticated
  USING (true);

-- municipios: OPTIONAL — the current dashboard never queries this table and the
-- view doesn't join it. Add this only if you later expose municipios to the app.
-- ALTER TABLE municipios ENABLE ROW LEVEL SECURITY;
-- DROP POLICY IF EXISTS "Public read access" ON municipios;
-- CREATE POLICY "Public read access" ON municipios
--   FOR SELECT
--   TO anon, authenticated
--   USING (true);


-- ---------------------------------------------------------------------------
-- 4. Verify the view works
-- ---------------------------------------------------------------------------
-- SELECT property_id, base_type, listing_status, last_seen_year,
--        price_changed, price_change_pct, days_tracked, region_clean
-- FROM properties_enriched
-- LIMIT 10;
