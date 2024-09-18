import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from urllib.parse import urlparse

import dns
import whois
from geolite2 import geolite2


def get_domain_data(domain_url: str):
    def _first(item):
        return item[0] if isinstance(item, list) else item

    details = DomainDetails(domain_url)

    # WHOIS
    whois_lookup = whois.whois(domain_url)
    details.whois_domain = _first(whois_lookup["domain_name"]).lower()
    details.whois_registrar = whois_lookup.get("registrar", whois_lookup.get("name", "Unknown"))
    creation_date = _first(whois_lookup["creation_date"])
    expiration_date = _first(whois_lookup["expiration_date"])
    details.whois_domain_lifetime = expiration_date - creation_date
    # DNS
    dns_query = dns.resolver.resolve(details.whois_domain, "A")
    details.dns_ip_addresses = [ipval.to_text() for ipval in dns_query]
    # GeoIP
    reader = geolite2.reader()
    geoip_query = reader.get(details.dns_ip_addresses[0])
    details.geo_ip_country = geoip_query["country"]["names"][
        "en"] if geoip_query and "country" in geoip_query else "Unknown"

    print(details)
    return details

class Url:
    def __init__(self, url: str):
        self._url = url

    @property
    def scheme(self) -> str:
        return urlparse(self._url).scheme

    @property
    def domain(self) -> str:
        return urlparse(self._url).netloc

    def __str__(self) -> str:
        return self._url

    def __repr__(self) -> str:
        return self._url

@dataclass
class DomainDetails:
    domain: str
    whois_domain: str | None = None
    whois_registrar: str | None = None
    whois_domain_lifetime: timedelta | None = None
    dns_ip_addresses: list[str] | None = None
    geo_ip_country: str | None = None

class ImportSource(StrEnum):
    CLEAN = "clean"
    PHISHTANK = "phishtank"

class Database:
    def __init__(self, name: str):
        self._conn = sqlite3.connect(name)
        self._cursor = self._conn.cursor()
        self._cursor.execute('''CREATE TABLE IF NOT EXISTS domains
             (domain text primary key, url text, source text NOT NULL, whois_domain text, whois_registrar text, whois_domain_lifetime int, dns_ip_addresses text, geo_ip_country text, whois_registrar_norm text, export integer)''')
        self._cursor.execute('''CREATE UNIQUE INDEX IF NOT EXISTS uq_whois_domain ON domains (whois_domain)''')
        self._conn.commit()

    def add_url(self, url: Url, source: ImportSource):
        try:
            self._cursor.execute("INSERT INTO domains(domain, url, source) VALUES (?, ?, ?)",
                                 [url.domain, str(url), str(source)])
            self._conn.commit()
        except sqlite3.IntegrityError:
            pass

    def update_domains(self):
        self._cursor.execute("SELECT domain FROM domains WHERE whois_registrar IS NULL OR whois_registrar=''")
        for row in self._cursor.fetchall():
            domain = row[0]
            try:
                self.update_domain(get_domain_data(domain))
            except Exception as e:
                print(f"Deleting {domain}. Reason: {e}", file=sys.stderr)
                self.delete_domain(domain)

    def update_domain(self, detail: DomainDetails):
        result = self._cursor.execute("SELECT whois_domain FROM domains WHERE domain=?", [detail.domain])
        row = result.fetchone()
        if row is not None and (row == (None,) or ('',)):
            self._cursor.execute(
                "UPDATE domains SET whois_domain=?, whois_registrar=?, whois_domain_lifetime=?, dns_ip_addresses=?, geo_ip_country=? WHERE domain=?",
                [detail.whois_domain, detail.whois_registrar, detail.whois_domain_lifetime.days,
                 ','.join(detail.dns_ip_addresses), detail.geo_ip_country, detail.domain])
            self._conn.commit()

    def delete_domain(self, domain: str):
        self._cursor.execute("DELETE FROM domains WHERE domain=?", [domain])
        self._conn.commit()

    def normalize_registrars(self):
        self._cursor.execute("SELECT domain, whois_registrar FROM domains")
        for row in self._cursor.fetchall():
            registrar = str(row[1]).upper()
            registrar = registrar.split(",")[0]
            registrar = re.sub(" INC\\.?", "", registrar)
            registrar = re.sub("\\[.*\\]", "", registrar)
            # Name-specific
            registrar = re.sub("1API", "1 API", registrar)
            registrar = re.sub("S\\.A$", "S.A.", registrar)
            registrar = registrar.strip()
            self._cursor.execute("UPDATE domains SET whois_registrar_norm=? WHERE domain = ?", [registrar, row[0]])
            self._conn.commit()

    def export(self):
        self._cursor.execute(
            "select url, whois_domain, source, whois_registrar_norm, whois_domain_lifetime / 365, geo_ip_country from domains where export = 1 order by source, domain")
        for row in self._cursor:
            print(",".join([str(r).replace(",", ".") for r in row]))

    def generate_freq_table(self, source: ImportSource):
        self._cursor.execute(
            "select whois_registrar_norm, whois_domain_lifetime / 365, geo_ip_country from domains where source=? and export = 1",
            [str(source)])
        registrars = {}
        lifetimes = {}
        countries = {}
        for row in self._cursor:
            registrar, lifetime, country = row
            registrars[registrar] = registrars.get(registrar, 0) + 1
            lifetimes[lifetime] = lifetimes.get(lifetime, 0) + 1
            countries[country] = countries.get(country, 0) + 1

        print("Source: ", source)
        for r in sorted(registrars.keys()):
            print(f"{r}, {registrars[r]}")
        print()
        for r in sorted(lifetimes.keys()):
            print(f"{r}, {lifetimes[r]}")
        print()
        for r in sorted(countries.keys()):
            print(f"{r}, {countries[r]}")

    def generate_data_set(self):
        self._cursor.execute("select distinct whois_registrar_norm from domains")
        registrar_names = [r[0] for r in self._cursor.fetchall()]
        self._cursor.execute(
            "select whois_registrar_norm, source, whois_domain_lifetime / 365, geo_ip_country from domains where export=1")

        header = registrar_names[:]
        header.extend(["lifetime", "country", "is_phish"])
        print(",".join(header))
        for r in self._cursor.fetchall():
            dataset_row = []
            registrar, source, lifetime, country = r

            registrar_flags = []
            for registrar_name in registrar_names:
                registrar_flags.append(1) if registrar == registrar_name else registrar_flags.append(0)

            dataset_row.extend(registrar_flags)
            dataset_row.append(lifetime)
            dataset_row.append(sum([ord(l) for l in country]))
            dataset_row.append(1 if source == 'phishtank' else 0)
            print(",".join([str(v) for v in dataset_row]))
