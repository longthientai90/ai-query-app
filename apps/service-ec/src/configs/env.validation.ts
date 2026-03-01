// Minimal env validation without extra dependencies.
export const validateEnv = () => {
  const {
    PORT,
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    DB_SSL,
    DB_SYNC,
    DB_LOGGING,
  } = process.env;

  if (PORT && Number.isNaN(Number(PORT))) {
    throw new Error('Invalid PORT. It must be a number.');
  }

  const requiredVars: Array<[string, string | undefined]> = [
    ['DB_HOST', DB_HOST],
    ['DB_PORT', DB_PORT],
    ['DB_USER', DB_USER],
    ['DB_PASSWORD', DB_PASSWORD],
    ['DB_NAME', DB_NAME],
  ];

  for (const [name, value] of requiredVars) {
    if (!value) {
      throw new Error(`Missing required env var: ${name}`);
    }
  }

  if (DB_PORT && Number.isNaN(Number(DB_PORT))) {
    throw new Error('Invalid DB_PORT. It must be a number.');
  }

  const boolVars: Array<[string, string | undefined]> = [
    ['DB_SSL', DB_SSL],
    ['DB_SYNC', DB_SYNC],
    ['DB_LOGGING', DB_LOGGING],
  ];

  for (const [name, value] of boolVars) {
    if (value !== undefined && value !== 'true' && value !== 'false') {
      throw new Error(`Invalid ${name}. It must be 'true' or 'false'.`);
    }
  }
};
