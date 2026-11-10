CREATE TABLE IF NOT EXISTS public.supabase_connection_test (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    status TEXT NOT NULL CHECK (status = 'ok')
);

ALTER TABLE public.supabase_connection_test ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON public.supabase_connection_test TO anon, authenticated;

DROP POLICY IF EXISTS "Allow read-only Supabase connection check"
    ON public.supabase_connection_test;

CREATE POLICY "Allow read-only Supabase connection check"
    ON public.supabase_connection_test
    FOR SELECT
    TO anon, authenticated
    USING (true);

INSERT INTO public.supabase_connection_test (id, status)
VALUES (1, 'ok')
ON CONFLICT (id) DO NOTHING;
