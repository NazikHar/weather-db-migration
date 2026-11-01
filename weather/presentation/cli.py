"""Консольний інтерфейс.

    python -m weather.presentation.cli import [--csv шлях]
    python -m weather.presentation.cli stats
"""

from __future__ import annotations

import argparse
from pathlib import Path

from weather.config import default_csv_path, get_database_url
from weather.data.database import make_engine, session_scope
from weather.data.repositories import WeatherObservationRepository
from weather.services.import_service import ImportService


def cmd_import(args: argparse.Namespace) -> None:
    engine = make_engine()
    path = Path(args.csv) if args.csv else default_csv_path()
    print(f"База: {get_database_url()}\nCSV: {path}")
    report = ImportService(engine).import_csv(path)
    print(
        f"Рядків у CSV: {report.total_rows}, вставлено: {report.inserted}, "
        f"пропущено (вже були): {report.skipped_existing}"
    )


def cmd_stats(args: argparse.Namespace) -> None:
    engine = make_engine()
    with session_scope(engine) as session:
        repo = WeatherObservationRepository(session)
        print(f"База: {get_database_url()}")
        print(f"Спостережень у weather_observations: {repo.count()}")
        for obs in repo.all(limit=3):
            print(" ", obs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weather", description="Погодна БД — CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="завантажити CSV у базу")
    p_import.add_argument("--csv", help="шлях до CSV (за замовчуванням data/...)")
    p_import.set_defaults(func=cmd_import)

    p_stats = sub.add_parser("stats", help="кількість записів у базі")
    p_stats.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
