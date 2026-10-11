"""Команда: генерация демо-данных (для запуска без Kaggle-датасета и в Docker)."""
import math
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from sales.models import MacroIndicator, SalesTransaction
from sales.utils import week_start_of

REGIONS = {
    "Northeast": ["NY", "MA", "PA"], "Midwest": ["IL", "OH", "MI"],
    "South": ["TX", "FL", "GA"], "West": ["CA", "WA", "CO"],
}
REGION_WEIGHT = {"Northeast": 0.8, "Midwest": 0.9, "South": 1.3, "West": 1.1}
CATEGORIES = {  # категория: (товары, базовая цена, чувствительность к стройке)
    "Lumber": (["2x4 Stud", "Plywood 4x8", "OSB Panel"], 8.0, 1.4),
    "Cement & Concrete": (["Portland Cement 94lb", "Ready-Mix Bag", "Mortar Mix"], 14.0, 1.0),
    "Roofing": (["Asphalt Shingles", "Metal Roofing Panel", "Underlayment"], 38.0, 0.9),
    "Insulation": (["Fiberglass Batt", "Spray Foam Kit", "Rigid Foam Board"], 24.0, 0.7),
    "Drywall": (["Drywall 4x8", "Joint Compound", "Drywall Screws"], 12.0, 1.1),
    "Plumbing": (["PVC Pipe 10ft", "Copper Fitting", "PEX Tubing"], 18.0, 0.5),
    "Electrical": (["Romex Wire 250ft", "Breaker Panel", "Outlet Box"], 30.0, 0.5),
}
BRANDS = ["BuildPro", "Keystone", "Atlas", "Summit", "Ironwood"]
CHANNELS = {"Retail": 0.04, "Wholesale": 0.12, "Online": 0.06, "Contractor Direct": 0.15}
SEGMENTS = {"Contractor": 1.0, "DIY": 0.6, "Developer": 1.8, "Government": 1.4}


class Command(BaseCommand):
    """Создаёт правдоподобные данные с сезонностью, трендом и связью с макропоказателями."""

    help = "Генерирует демо-данные продаж (2019–2024) и недельные макропоказатели."

    def add_arguments(self, parser):
        parser.add_argument("--rows", type=int, default=30000)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--truncate", action="store_true")

    def handle(self, *args, **opts):
        rng = random.Random(opts["seed"])
        weeks = []
        day = week_start_of(date(2019, 1, 1))
        while day <= date(2024, 12, 30):
            weeks.append(day)
            day += timedelta(days=7)

        macro, macro_rows = {}, []
        for i, week in enumerate(weeks):
            t = i / len(weeks)
            season = math.sin((week.timetuple().tm_yday - 80) / 365 * 2 * math.pi)
            starts = 1250 + 180 * season + 150 * t + rng.gauss(0, 40)
            mortgage = 3.9 - 1.2 * min(t * 3, 1) + 4.2 * max(t - 0.45, 0) + rng.gauss(0, 0.05)
            cost_index = 100 + 28 * max(0, min((t - 0.3) * 3, 1)) + 6 * t + rng.gauss(0, 0.8)
            lumber = 100 + 70 * math.exp(-((t - 0.38) ** 2) / 0.005) + rng.gauss(0, 3)
            unemployment = 3.6 + 11 * math.exp(-((t - 0.17) ** 2) / 0.0008) - 0.4 * t + rng.gauss(0, 0.1)
            macro[week] = {"housing_starts": starts, "mortgage_rate": mortgage, "construction_cost_index": cost_index,
                           "lumber_price_index": lumber, "unemployment_rate": unemployment, "season": season}
            for name in ("housing_starts", "mortgage_rate", "construction_cost_index", "lumber_price_index", "unemployment_rate"):
                macro_rows.append(MacroIndicator(week_start=week, indicator=name, value=round(macro[week][name], 3)))

        weights = [max(0.1, 1 + 0.45 * macro[w]["season"] + 0.0006 * (macro[w]["housing_starts"] - 1250)) for w in weeks]
        objs = []
        for n in range(opts["rows"]):
            week = rng.choices(weeks, weights)[0]
            m = macro[week]
            region = rng.choices(list(REGIONS), [REGION_WEIGHT[r] for r in REGIONS])[0]
            category = rng.choice(list(CATEGORIES))
            products, base, sensitivity = CATEGORIES[category]
            channel = rng.choice(list(CHANNELS))
            segment = rng.choices(list(SEGMENTS), [5, 3, 1.5, 1])[0]
            price = base * (m["construction_cost_index"] / 100) * (m["lumber_price_index"] / 100 if category == "Lumber" else 1)
            price *= rng.uniform(0.92, 1.08)
            discount = max(0.0, CHANNELS[channel] + rng.gauss(0, 0.02))
            demand = SEGMENTS[segment] * (1 + sensitivity * (m["housing_starts"] - 1250) / 1250) * (1 + 0.3 * (4 - m["mortgage_rate"]) / 4)
            qty = max(1, round(rng.lognormvariate(3.0, 0.7) * max(demand, 0.2)))
            revenue = qty * price * (1 - discount)
            day = week + timedelta(days=rng.randint(0, 6))
            objs.append(SalesTransaction(
                transaction_id=f"DEMO-{n + 1:07d}", date=day, week_start=week,
                region=region, state=rng.choice(REGIONS[region]), category=category,
                product=rng.choice(products), brand=rng.choice(BRANDS), customer_segment=segment,
                sales_channel=channel, quantity=Decimal(qty), unit_price=Decimal(f"{price:.2f}"),
                discount_pct=Decimal(f"{discount * 100:.3f}"), revenue=Decimal(f"{revenue:.2f}"),
                cost=Decimal(f"{revenue * rng.uniform(0.62, 0.8):.2f}"), extra={"demo": True}))

        with transaction.atomic():
            if opts["truncate"]:
                SalesTransaction.objects.all().delete()
                MacroIndicator.objects.all().delete()
            MacroIndicator.objects.bulk_create(macro_rows, batch_size=5000, update_conflicts=True,
                                               unique_fields=["week_start", "indicator"], update_fields=["value"])
            SalesTransaction.objects.bulk_create(objs, batch_size=5000)
        self.stdout.write(self.style.SUCCESS(f"Демо-данные: {len(objs)} продаж, {len(macro_rows)} макро-значений."))
