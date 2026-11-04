import argparse
import logging
from pathlib import Path

from app.analytics.powerbi_exporter import POWERBI_DIR, export_powerbi
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o modelo estrela do CyberSim AI para CSV.")
    parser.add_argument("--output", type=Path, default=POWERBI_DIR, help="Diretório de destino dos CSVs.")
    parser.add_argument("--company-id", help="Exporta somente uma empresa autorizada.")
    args = parser.parse_args()

    with SessionLocal() as db:
        result = export_powerbi(db, args.output, args.company_id)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.info(
        "Exportação concluída: %s registros em %s",
        result["total_rows"],
        args.output.resolve(),
    )
    for table, count in sorted(result["counts"].items()):
        logging.info("%s: %s", table, count)


if __name__ == "__main__":
    main()
