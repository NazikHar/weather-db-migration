"""Консольний інтерфейс.

    python -m weather.presentation.cli import [--csv шлях]
    python -m weather.presentation.cli stats
    python -m weather.presentation.cli fill-go-outside [--all]
    python -m weather.presentation.cli query --country Ukraine --date 2024-07-15 [--city Kyiv] [--safe|--unsafe]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from weather.config import default_csv_path, get_database_url
from weather.data.database import make_engine, session_scope
from weather.data.repositories import AirQualityRepository, WeatherObservationRepository
from weather.services.air_quality_service import AirQualityService
from weather.services.import_service import ImportService
from weather.services.weather_query_service import WeatherQueryService, WeatherReport


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
        print(f"Записів у air_quality: {AirQualityRepository(session).count()}")
        for obs in repo.all(limit=3):
            print(" ", obs, obs.air_quality)


def cmd_fill_go_outside(args: argparse.Namespace) -> None:
    engine = make_engine()
    service = AirQualityService(engine)
    print(f"База: {get_database_url()}")
    report = service.fill_is_safe_to_go_outside(only_missing=not args.all)
    print(f"Оновлено: {report.updated} (варто виходити: {report.safe}, не варто: {report.unsafe})")
    dist = service.distribution()
    print("Розподіл у таблиці air_quality:", {str(k): v for k, v in dist.items()})


EPA_LABELS = {1: "Good", 2: "Moderate", 3: "Unhealthy for sensitive groups",
              4: "Unhealthy", 5: "Very Unhealthy", 6: "Hazardous"}


def _print_report(r: WeatherReport) -> None:
    flag = {True: "ТАК", False: "НІ", None: "не обчислено"}[r.is_safe_to_go_outside]
    print(f"\n{'=' * 70}\n{r.country} — {r.city}   {r.last_updated:%Y-%m-%d %H:%M}\n{'=' * 70}")
    print(f"  Погода:            {r.condition_text}, {r.temperature_celsius:+.1f} °C, вологість {r.humidity} %")
    print(f"  Вітер:             {r.wind_kph} км/год, {r.wind_degree}° ({r.wind_direction})")
    print(f"  Схід / захід:      {r.sunrise:%H:%M} / {r.sunset:%H:%M}")
    print("  Стан повітря (мкг/м³):")
    print(f"    CO {r.carbon_monoxide:8.1f}   O3 {r.ozone:6.1f}   NO2 {r.nitrogen_dioxide:6.1f}   SO2 {r.sulphur_dioxide:6.1f}")
    print(f"    PM2.5 {r.pm2_5:6.1f}   PM10 {r.pm10:6.1f}")
    print(f"    US EPA index: {r.us_epa_index} ({EPA_LABELS.get(r.us_epa_index, '?')}),   GB DEFRA index: {r.gb_defra_index}")
    print(f"  Чи варто виходити: {flag}  →  {r.go_outside_explanation}")


def cmd_query(args: argparse.Namespace) -> None:
    engine = make_engine()
    try:
        day = date.fromisoformat(args.date)
    except ValueError:
        sys.exit(f"Дата має бути у форматі YYYY-MM-DD, отримано: {args.date!r}")
    safe_only = True if args.safe else (False if args.unsafe else None)
    result = WeatherQueryService(engine).by_country_and_date(
        country=args.country, day=day, city=args.city, safe_only=safe_only
    )
    if not result.reports:
        print(f"Нічого не знайдено для «{args.country}» за {day}.")
        if result.country_suggestions:
            print("Можливо, ви мали на увазі:", ", ".join(result.country_suggestions))
        return
    for r in result.reports:
        _print_report(r)
    print(f"\nЗнайдено спостережень: {len(result.reports)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weather", description="Погодна БД — CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="завантажити CSV у базу")
    p_import.add_argument("--csv", help="шлях до CSV (за замовчуванням data/...)")
    p_import.set_defaults(func=cmd_import)

    p_stats = sub.add_parser("stats", help="кількість записів у базі")
    p_stats.set_defaults(func=cmd_stats)

    p_fill = sub.add_parser(
        "fill-go-outside", help="обчислити колонку «чи варто виходити» (етап 3)"
    )
    p_fill.add_argument("--all", action="store_true", help="перерахувати всі рядки, не лише NULL")
    p_fill.set_defaults(func=cmd_fill_go_outside)

    p_query = sub.add_parser("query", help="уся погода за країною та датою (етап 4)")
    p_query.add_argument("--country", required=True, help="назва країни англійською, напр. Ukraine")
    p_query.add_argument("--date", required=True, help="дата YYYY-MM-DD")
    p_query.add_argument("--city", help="місто (необов'язково), напр. Kyiv")
    flag = p_query.add_mutually_exclusive_group()
    flag.add_argument("--safe", action="store_true", help="лише де варто виходити")
    flag.add_argument("--unsafe", action="store_true", help="лише де не варто виходити")
    p_query.set_defaults(func=cmd_query)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
