-- ============================================================
-- AI Power Blackout Predictor — Row Level Security Policies
-- Run this in the Supabase SQL Editor AFTER bootstrap_supabase.sql
-- Safe to re-run: all statements use IF NOT EXISTS / DROP POLICY IF EXISTS.
--
-- Access model:
--   service_role  — backend API (bypasses RLS automatically)
--   authenticated — logged-in Supabase Auth users (not used in this project
--                   because we use our own JWT, but policies are defined for
--                   defence-in-depth / PostgREST direct-access hardening)
--   anon          — unauthenticated requests to PostgREST
--
-- Rule: anon gets read-only on public-safe tables; everything else requires
-- service_role (i.e., no row is accessible via anon/authenticated by default).
-- ============================================================

-- ── PostGIS system table ──────────────────────────────────────────────────────
ALTER TABLE public.spatial_ref_sys ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "spatial_ref_sys_select" ON public.spatial_ref_sys;
CREATE POLICY "spatial_ref_sys_select"
    ON public.spatial_ref_sys FOR SELECT TO anon, authenticated USING (true);

-- ════════════════════════════════════════════════════════════
--  PUBLIC-READ tables (geographic / prediction data)
-- ════════════════════════════════════════════════════════════

-- h3_cells
ALTER TABLE public.h3_cells ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "h3_cells_anon_select" ON public.h3_cells;
CREATE POLICY "h3_cells_anon_select"
    ON public.h3_cells FOR SELECT TO anon, authenticated USING (true);

-- predictions
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "predictions_anon_select" ON public.predictions;
CREATE POLICY "predictions_anon_select"
    ON public.predictions FOR SELECT TO anon, authenticated USING (true);

-- outage_reports (public read — no PII exposed)
ALTER TABLE public.outage_reports ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "outage_reports_anon_select" ON public.outage_reports;
CREATE POLICY "outage_reports_anon_select"
    ON public.outage_reports FOR SELECT TO anon, authenticated USING (true);

-- neighborhood_stats
ALTER TABLE public.neighborhood_stats ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "neighborhood_stats_anon_select" ON public.neighborhood_stats;
CREATE POLICY "neighborhood_stats_anon_select"
    ON public.neighborhood_stats FOR SELECT TO anon, authenticated USING (true);

-- prediction_accuracy
ALTER TABLE public.prediction_accuracy ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "prediction_accuracy_anon_select" ON public.prediction_accuracy;
CREATE POLICY "prediction_accuracy_anon_select"
    ON public.prediction_accuracy FOR SELECT TO anon, authenticated USING (true);

-- seasonal_stats
ALTER TABLE public.seasonal_stats ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "seasonal_stats_anon_select" ON public.seasonal_stats;
CREATE POLICY "seasonal_stats_anon_select"
    ON public.seasonal_stats FOR SELECT TO anon, authenticated USING (true);

-- resilience_scores
ALTER TABLE public.resilience_scores ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "resilience_scores_anon_select" ON public.resilience_scores;
CREATE POLICY "resilience_scores_anon_select"
    ON public.resilience_scores FOR SELECT TO anon, authenticated USING (true);

-- poi_locations
ALTER TABLE public.poi_locations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "poi_locations_anon_select" ON public.poi_locations;
CREATE POLICY "poi_locations_anon_select"
    ON public.poi_locations FOR SELECT TO anon, authenticated USING (true);

-- poi_status_reports (public read)
ALTER TABLE public.poi_status_reports ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "poi_status_reports_anon_select" ON public.poi_status_reports;
CREATE POLICY "poi_status_reports_anon_select"
    ON public.poi_status_reports FOR SELECT TO anon, authenticated USING (true);

-- planned_outages (public read — scheduled maintenance)
ALTER TABLE public.planned_outages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "planned_outages_anon_select" ON public.planned_outages;
CREATE POLICY "planned_outages_anon_select"
    ON public.planned_outages FOR SELECT TO anon, authenticated USING (true);

-- restoration_events (public read)
ALTER TABLE public.restoration_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "restoration_events_anon_select" ON public.restoration_events;
CREATE POLICY "restoration_events_anon_select"
    ON public.restoration_events FOR SELECT TO anon, authenticated USING (true);

-- grid_transformers (public read — no sensitive data)
ALTER TABLE public.grid_transformers ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "grid_transformers_anon_select" ON public.grid_transformers;
CREATE POLICY "grid_transformers_anon_select"
    ON public.grid_transformers FOR SELECT TO anon, authenticated USING (true);

-- transformer_cell_coverage
ALTER TABLE public.transformer_cell_coverage ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "transformer_cell_coverage_anon_select" ON public.transformer_cell_coverage;
CREATE POLICY "transformer_cell_coverage_anon_select"
    ON public.transformer_cell_coverage FOR SELECT TO anon, authenticated USING (true);

-- grid_load_snapshots
ALTER TABLE public.grid_load_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "grid_load_snapshots_anon_select" ON public.grid_load_snapshots;
CREATE POLICY "grid_load_snapshots_anon_select"
    ON public.grid_load_snapshots FOR SELECT TO anon, authenticated USING (true);

-- gnn_predictions
ALTER TABLE public.gnn_predictions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "gnn_predictions_anon_select" ON public.gnn_predictions;
CREATE POLICY "gnn_predictions_anon_select"
    ON public.gnn_predictions FOR SELECT TO anon, authenticated USING (true);

-- region_similarities
ALTER TABLE public.region_similarities ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "region_similarities_anon_select" ON public.region_similarities;
CREATE POLICY "region_similarities_anon_select"
    ON public.region_similarities FOR SELECT TO anon, authenticated USING (true);

-- community_notes (public read)
ALTER TABLE public.community_notes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "community_notes_anon_select" ON public.community_notes;
CREATE POLICY "community_notes_anon_select"
    ON public.community_notes FOR SELECT TO anon, authenticated USING (true);

-- note_upvotes (public read)
ALTER TABLE public.note_upvotes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "note_upvotes_anon_select" ON public.note_upvotes;
CREATE POLICY "note_upvotes_anon_select"
    ON public.note_upvotes FOR SELECT TO anon, authenticated USING (true);

-- neighbor_alert_log (public read)
ALTER TABLE public.neighbor_alert_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "neighbor_alert_log_anon_select" ON public.neighbor_alert_log;
CREATE POLICY "neighbor_alert_log_anon_select"
    ON public.neighbor_alert_log FOR SELECT TO anon, authenticated USING (true);

-- prediction_feedback (public read)
ALTER TABLE public.prediction_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "prediction_feedback_anon_select" ON public.prediction_feedback;
CREATE POLICY "prediction_feedback_anon_select"
    ON public.prediction_feedback FOR SELECT TO anon, authenticated USING (true);

-- outage_incidents (public read)
ALTER TABLE public.outage_incidents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "outage_incidents_anon_select" ON public.outage_incidents;
CREATE POLICY "outage_incidents_anon_select"
    ON public.outage_incidents FOR SELECT TO anon, authenticated USING (true);

-- ════════════════════════════════════════════════════════════
--  SERVICE-ROLE-ONLY tables (no direct anon/authenticated access)
--  These tables contain PII or sensitive operational data.
--  All access goes through the backend API (service_role bypasses RLS).
-- ════════════════════════════════════════════════════════════

-- users (PII — phone, email, password_hash)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
-- No anon/authenticated policies: only service_role can read/write.

-- user_locations
ALTER TABLE public.user_locations ENABLE ROW LEVEL SECURITY;

-- alert_subscriptions
ALTER TABLE public.alert_subscriptions ENABLE ROW LEVEL SECURITY;

-- push_subscriptions
ALTER TABLE public.push_subscriptions ENABLE ROW LEVEL SECURITY;

-- whatsapp_subscriptions
ALTER TABLE public.whatsapp_subscriptions ENABLE ROW LEVEL SECURITY;

-- telegram_subscriptions
ALTER TABLE public.telegram_subscriptions ENABLE ROW LEVEL SECURITY;

-- email_subscriptions
ALTER TABLE public.email_subscriptions ENABLE ROW LEVEL SECURITY;

-- sms_alerts (delivery records with phone numbers)
ALTER TABLE public.sms_alerts ENABLE ROW LEVEL SECURITY;

-- user_points
ALTER TABLE public.user_points ENABLE ROW LEVEL SECURITY;

-- user_badges
ALTER TABLE public.user_badges ENABLE ROW LEVEL SECURITY;

-- point_transactions
ALTER TABLE public.point_transactions ENABLE ROW LEVEL SECURITY;

-- insurance_policies (financial data)
ALTER TABLE public.insurance_policies ENABLE ROW LEVEL SECURITY;

-- insurance_claims (financial data)
ALTER TABLE public.insurance_claims ENABLE ROW LEVEL SECURITY;

-- business_profiles
ALTER TABLE public.business_profiles ENABLE ROW LEVEL SECURITY;

-- webhook_subscriptions (contains secret keys)
ALTER TABLE public.webhook_subscriptions ENABLE ROW LEVEL SECURITY;

-- webhook_events
ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;

-- fraud_flags (security-sensitive)
ALTER TABLE public.fraud_flags ENABLE ROW LEVEL SECURITY;

-- sms_inbound_log
ALTER TABLE public.sms_inbound_log ENABLE ROW LEVEL SECURITY;

-- utility_companies (contains API keys)
ALTER TABLE public.utility_companies ENABLE ROW LEVEL SECURITY;

-- ivr_calls
ALTER TABLE public.ivr_calls ENABLE ROW LEVEL SECURITY;

-- prepaid_meters (user financial data)
ALTER TABLE public.prepaid_meters ENABLE ROW LEVEL SECURITY;

-- prepaid_topup_reminders
ALTER TABLE public.prepaid_topup_reminders ENABLE ROW LEVEL SECURITY;

-- medical_priority_users (sensitive health data)
ALTER TABLE public.medical_priority_users ENABLE ROW LEVEL SECURITY;

-- data_export_requests
ALTER TABLE public.data_export_requests ENABLE ROW LEVEL SECURITY;

-- white_label_configs (contains branding secrets)
ALTER TABLE public.white_label_configs ENABLE ROW LEVEL SECURITY;

-- dispatch_recommendations (operational)
ALTER TABLE public.dispatch_recommendations ENABLE ROW LEVEL SECURITY;

-- regulatory_reports
ALTER TABLE public.regulatory_reports ENABLE ROW LEVEL SECURITY;

-- subscription_plans (readable by service_role to enforce limits)
ALTER TABLE public.subscription_plans ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "subscription_plans_anon_select" ON public.subscription_plans;
CREATE POLICY "subscription_plans_anon_select"
    ON public.subscription_plans FOR SELECT TO anon, authenticated USING (true);

-- user_subscriptions (billing data)
ALTER TABLE public.user_subscriptions ENABLE ROW LEVEL SECURITY;

-- billing_events
ALTER TABLE public.billing_events ENABLE ROW LEVEL SECURITY;

-- public_api_keys (contains key hashes — do NOT expose)
ALTER TABLE public.public_api_keys ENABLE ROW LEVEL SECURITY;

-- public_api_usage
ALTER TABLE public.public_api_usage ENABLE ROW LEVEL SECURITY;

-- admin_audit_logs (strictly internal — no external access)
ALTER TABLE public.admin_audit_logs ENABLE ROW LEVEL SECURITY;
