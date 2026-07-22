from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.config import get_settings
from backend.models.user import User
from backend.routes.deps import get_optional_user

router = APIRouter(tags=["pages"])
settings = get_settings()
templates = Jinja2Templates(directory=str(settings.base_dir / "src" / "frontend" / "templates"))


@router.get("/")
def root(user: User | None = Depends(get_optional_user)):
    if user is None:
        return RedirectResponse("/info")
    if user.role.value == "patient":
        return RedirectResponse("/app")
    return RedirectResponse("/staff")


@router.get("/info")
def info_page(request: Request):
    return templates.TemplateResponse(request, "info.html")


@router.get("/login")
def login_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user is not None:
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "auth/login.html")


@router.get("/register")
def register_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user is not None:
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "auth/register.html")


@router.get("/app")
def patient_dashboard(request: Request, user: User | None = Depends(get_optional_user)):
    if user is None:
        return RedirectResponse("/login")
    if user.role.value != "patient":
        return RedirectResponse("/staff")
    return templates.TemplateResponse(request, "patient/dashboard.html", {"user": user})


@router.get("/staff")
def staff_dashboard(request: Request, user: User | None = Depends(get_optional_user)):
    if user is None:
        return RedirectResponse("/login")
    if user.role.value not in ("staff", "admin"):
        return RedirectResponse("/app")
    return templates.TemplateResponse(request, "staff/dashboard.html", {"user": user})
