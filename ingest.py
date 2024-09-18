import re
from os import listdir
from os.path import isfile, join

from datasource import Database, ImportSource, Url


class PhishTankDirectory:
    """
    Imports all files in a directory. Their contents are expected to match the format in sample.txt.
    """
    def __init__(self, path: str):
        self._path = path

    def _import_file(self, filename: str) -> list[Url]:
        urls = []
        with open(f"{self._path}/{filename}", "r") as file:
            for line in file:
                m = re.search('^[0-9]+\\s+(http.*)', line.strip())
                if m:
                    urls.append(Url(m.group(1).strip(".")))
        return urls

    def import_all(self) -> list[Url]:
        urls = []
        for f in [f for f in listdir(self._path) if isfile(join(self._path, f))]:
            urls.extend(self._import_file(f))
        return urls

def ingest_top_500_sites(db: Database):
    with open("top500.txt", "r") as f:
        for s in f:
            db.add_url(Url(s.strip()), ImportSource.CLEAN)

def ingest_phishtank_sites(db: Database):
    for url in PhishTankDirectory("phishtank").import_all():
        db.add_url(url, ImportSource.PHISHTANK)
