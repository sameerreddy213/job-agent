"""Deterministic job fingerprint for cross-source deduplication.

fingerprint = SHA256( norm(company) | norm(title) | norm(location) )
"""
import hashlib
import re

_WS = re.compile(r"\s+")


def _norm(value: str | None) -> str:
    return _WS.sub(" ", (value or "").strip().lower())


def fingerprint(company: str | None, title: str | None, location: str | None) -> str:
    basis = f"{_norm(company)}|{_norm(title)}|{_norm(location)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()
