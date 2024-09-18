from datasource import *
from ingest import ingest_top_500_sites, ingest_phishtank_sites


if __name__ == '__main__':
    db = Database("domains.db")
    ingest_top_500_sites(db)
    ingest_phishtank_sites(db)
    db.update_domains()
    db.normalize_registrars()
    db.export()
    print()
    db.generate_freq_table(ImportSource.PHISHTANK)
    print()
    db.generate_freq_table(ImportSource.CLEAN)
    db.generate_data_set()
