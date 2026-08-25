from __future__ import annotations

from app.dashboard.service import DashboardStats


def test_dashboard_stats_defaults():
    stats = DashboardStats(
        total_items=0,
        total_categories=0,
        total_locations=0,
        total_tags=0,
        items_without_image=0,
        items_without_location=0,
        items_without_category=0,
    )
    assert stats.total_items == 0
    assert stats.items_without_image == 0


def test_dashboard_stats_with_data():
    stats = DashboardStats(
        total_items=42,
        total_categories=5,
        total_locations=3,
        total_tags=12,
        items_without_image=10,
        items_without_location=5,
        items_without_category=2,
    )
    assert stats.total_items == 42
    assert stats.items_without_image == 10
    assert stats.items_without_location == 5
    assert stats.items_without_category == 2
