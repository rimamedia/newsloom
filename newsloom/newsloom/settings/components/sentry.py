from newsloom.contrib.env import get_env_var

SENTRY_DSN = get_env_var(
    "SENTRY_DSN",
    default="https://bf849e3f2ff92db1569e3ae171c8b1e5@o4508924566175744.ingest.us.sentry.io/4508924569845760"
)