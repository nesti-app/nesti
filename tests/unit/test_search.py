from __future__ import annotations

import uuid

from app.search.service import SearchParams


def test_search_params_defaults():
    params = SearchParams()
    assert params.q is None
    assert params.category_id is None
    assert params.location_id is None
    assert params.tag_id is None
    assert params.sort == "name_asc"
    assert params.page == 1
    assert params.per_page == 20


def test_search_params_with_query():
    params = SearchParams(q="laptop", sort="date_desc", page=2)
    assert params.q == "laptop"
    assert params.sort == "date_desc"
    assert params.page == 2


def test_search_params_with_filters():
    cat_id = uuid.uuid4()
    loc_id = uuid.uuid4()
    tag_id = uuid.uuid4()
    params = SearchParams(
        category_id=cat_id,
        location_id=loc_id,
        tag_id=tag_id,
    )
    assert params.category_id == cat_id
    assert params.location_id == loc_id
    assert params.tag_id == tag_id


def test_search_sort_keys():
    from app.search.service import SORT_MAP

    assert "name_asc" in SORT_MAP
    assert "name_desc" in SORT_MAP
    assert "date_asc" in SORT_MAP
    assert "date_desc" in SORT_MAP
    assert "price_asc" in SORT_MAP
    assert "price_desc" in SORT_MAP
