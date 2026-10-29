from fastapi import APIRouter

from app.optimization.licenses import level_options, license_catalog

router = APIRouter(prefix="/api/licenses", tags=["licenses"])


@router.get("")
def list_licenses() -> list[dict]:
    """Rodzaje licencji pogrupowane do formularza sędziego, z opisem uprawnień."""
    return license_catalog()


@router.get("/levels")
def list_levels() -> list[str]:
    """Poziomy rozgrywek do wyboru jako preferowane ligi sędziego."""
    return level_options()
