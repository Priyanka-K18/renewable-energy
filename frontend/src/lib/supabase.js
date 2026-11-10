import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim();

const missingVariables = [
  !supabaseUrl && 'VITE_SUPABASE_URL',
  !supabasePublishableKey && 'VITE_SUPABASE_PUBLISHABLE_KEY',
].filter(Boolean);

if (missingVariables.length > 0) {
  throw new Error(
    `Missing Supabase environment variable(s): ${missingVariables.join(', ')}. ` +
      'Set them in frontend/.env.local and restart the Vite dev server.',
  );
}

try {
  const parsedUrl = new URL(supabaseUrl);
  if (parsedUrl.protocol !== 'https:' && parsedUrl.hostname !== 'localhost') {
    throw new Error('must use HTTPS outside localhost');
  }
} catch (error) {
  throw new Error(
    `VITE_SUPABASE_URL must be a valid HTTPS Supabase project URL. ${error.message}`,
  );
}

export const supabase = createClient(supabaseUrl, supabasePublishableKey);
