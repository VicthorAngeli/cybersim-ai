from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)
_rate_lock = Lock()
_rate_events: dict[str, deque[float]] = defaultdict(deque)
_rate_window_seconds = 60
_rate_limit = 20


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária.")
    payload = decode_access_token(credentials.credentials)
    user = db.scalar(select(User).where(User.id == payload.get("sub"), User.active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo ou inexistente.")
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil sem permissão para esta ação.")
        return user
    return dependency


def rate_limit_llm_request(user: User = Depends(get_current_user)) -> None:
    now = monotonic()
    with _rate_lock:
        recent = _rate_events[user.id]
        while recent and now - recent[0] >= _rate_window_seconds:
            recent.popleft()
        if len(recent) >= _rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Limite temporário de chamadas de IA atingido; tente novamente em um minuto.",
                headers={"Retry-After": str(_rate_window_seconds)},
            )
        recent.append(now)
