GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})

# A nonce is used within seconds of being issued; this is slack for a slow sign-in.
GOOGLE_NONCE_EXPIRE_MINUTES = 5
