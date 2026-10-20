from fastapi import APIRouter

from app.optimization.licenses import license_catalog

router = APIRouter(prefix="/api/licenses", tags=["licenses"])


@router.get("")
def list_licenses() -> list[dict]:
    """Rodzaje licencji pogrupowane do formularza sędziego, z opisem uprawnień."""
    return license_catalog()
