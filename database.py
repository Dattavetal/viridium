import os
from typing import Optional

from sqlmodel import SQLModel, Field, create_engine

# ---------------------------------------------------------------------------
# SQLite DB setup
# ---------------------------------------------------------------------------
db_url = "sqlite:///pfas_lens.db"
engine = create_engine(db_url, echo=False)


# ---------------------------------------------------------------------------
# Table Definitions
# ---------------------------------------------------------------------------

class Substance(SQLModel, table=True):
    cas: str = Field(primary_key=True)
    name: str
    smiles: Optional[str] = None
    synonyms: Optional[str] = None
    is_pfas: bool = False


class Alternative(SQLModel, table=True):
    id: str = Field(primary_key=True)
    alt_name: str
    use_case: Optional[str] = None
    notes: Optional[str] = None
    temp_limit_c: Optional[float] = None
    cost_index: Optional[float] = None


class BomItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    part_number: str
    description: str
    supplier: str
    cas: Optional[str] = None
    quantity: Optional[int] = 1


# ---------------------------------------------------------------------------
# Create Tables If DB Does Not Exist
# ---------------------------------------------------------------------------
if not os.path.exists("pfas_lens.db"):
    SQLModel.metadata.create_all(engine)
