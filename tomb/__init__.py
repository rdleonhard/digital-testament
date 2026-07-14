"""digital-testament: tooling for a will's Digital Persona Legacy article.

Endow -> stake -> converse. USD becomes staked VVV, staked VVV yields a daily
Diem inference allocation on Venice, and the Diem runs the testator's Digital
Persona built from a corpus JSON.

Stdlib only. Python 3.9+.
"""

import ssl

__version__ = "0.1.0"

VENICE_API_BASE = "https://api.venice.ai/api/v1"


def ssl_context() -> ssl.SSLContext:
    """Default TLS context, falling back to certifi's CA bundle when the
    interpreter has no system certs wired up (common on macOS python.org
    installs where Install Certificates.command was never run)."""
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats().get("x509_ca"):
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            pass
    return ctx
