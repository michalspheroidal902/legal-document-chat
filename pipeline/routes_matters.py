"""Matters router — list/create matters (the D-18 retrieval scope). Read + create only;
no matter is ever inferred from text (explicit selection only, D-35)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import catalog

router = APIRouter()


class NewMatter(BaseModel):
    display_name: str


@router.get("/matters")
def get_matters():
    return {"matters": catalog.list_matters()}


@router.post("/matters")
def post_matter(body: NewMatter):
    try:
        return catalog.create_matter(body.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
