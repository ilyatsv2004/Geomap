# app/main.py
# app/main.py
from fastapi import FastAPI, Query
from pydantic import BaseModel
import pandas as pd

from app.app import build_index, search_lev

app = FastAPI(title="Fuzzy Address Search")

# Загружаем данные один раз при старте приложения
DF = pd.read_csv("data/final_norm.csv")
DF_IDX, FULL_LIST, TRIGRAM_SETS, INVERTED = build_index(DF)


class SearchResponseObject(BaseModel):
    locality: str | None
    street: str | None
    number: str | None
    lon: float | None
    lat: float | None
    score: float


class SearchResponse(BaseModel):
    searched_address: str
    objects: list[SearchResponseObject]


@app.get("/search", response_model=SearchResponse)
def search_endpoint(
    q: str = Query(..., description="Адрес для поиска"),
    top_k: int = Query(1, ge=1, le=20, description="Сколько лучших кандидатов вернуть"),
):
    """
    Пример:
      /search?q=москва%20туристская%20улица%206к1&top_k=3
    """
    result = search_lev(
        query=q,
        df=DF_IDX,
        full_list=FULL_LIST,
        trigram_sets=TRIGRAM_SETS,
        inverted=INVERTED,
        top_k=top_k,
    )
    return result