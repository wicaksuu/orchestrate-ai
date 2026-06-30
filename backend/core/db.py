import base64
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pymysql
from cryptography.fernet import Fernet, InvalidToken

from config import settings
from core.schemas import AgentAISetting, AgentAISettingUpdate

logger = logging.getLogger(__name__)


class DatabaseManager:
    """MariaDB-backed settings store with in-memory fallback for tests/dev."""

    def __init__(self) -> None:
        self.use_fallback = False
        self._agent_ai_settings: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._fernet = Fernet(self._derive_key(settings.SECRET_KEY))

    def _derive_key(self, secret: str) -> bytes:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def _parse_database_url(self) -> dict:
        parsed = urlparse(settings.DATABASE_URL)
        return {
            "host": parsed.hostname or "mariadb",
            "port": parsed.port or 3306,
            "user": parsed.username or "sigma",
            "password": parsed.password or "",
            "database": (parsed.path or "/sigma").lstrip("/"),
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": True,
            "charset": "utf8mb4",
        }

    def _connect(self):
        return pymysql.connect(**self._parse_database_url())

    async def connect(self) -> None:
        import asyncio

        last_error: Exception | None = None
        for attempt in range(1, 11):
            try:
                await self._run_sync(self._init_schema)
                self.use_fallback = False
                logger.info("DatabaseManager connected to MariaDB.")
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "DatabaseManager MariaDB connection attempt %d/10 failed: %s",
                    attempt,
                    exc,
                )
                await asyncio.sleep(1)
        self.use_fallback = True
        logger.warning(
            "DatabaseManager failed to connect to MariaDB, using in-memory fallback: %s",
            last_error,
        )

    async def disconnect(self) -> None:
        return None

    async def _run_sync(self, func, *args):
        import asyncio

        return await asyncio.to_thread(func, *args)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_ai_settings (
                        project_id VARCHAR(128) NOT NULL,
                        agent_name VARCHAR(64) NOT NULL,
                        provider VARCHAR(32) NOT NULL,
                        model VARCHAR(128) NOT NULL,
                        api_key_cipher TEXT NULL,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (project_id, agent_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def _decrypt(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            logger.error("Failed to decrypt stored API key.")
            return None

    async def get_agent_ai_settings(self, project_id: str) -> List[AgentAISetting]:
        if self.use_fallback:
            rows = self._agent_ai_settings.get(project_id, {})
            return [
                AgentAISetting(
                    agent_name=agent_name,
                    provider=row["provider"],
                    model=row["model"],
                    api_key_configured=bool(row.get("api_key_cipher")),
                    updated_at=row.get("updated_at"),
                )
                for agent_name, row in rows.items()
            ]
        return await self._run_sync(self._get_agent_ai_settings_sync, project_id)

    def _get_agent_ai_settings_sync(self, project_id: str) -> List[AgentAISetting]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT agent_name, provider, model, api_key_cipher, updated_at
                    FROM agent_ai_settings
                    WHERE project_id = %s
                    ORDER BY agent_name
                    """,
                    (project_id,),
                )
                rows = cur.fetchall()
        return [
            AgentAISetting(
                agent_name=row["agent_name"],
                provider=row["provider"],
                model=row["model"],
                api_key_configured=bool(row.get("api_key_cipher")),
                updated_at=row.get("updated_at"),
            )
            for row in rows
        ]

    async def save_agent_ai_setting(
        self,
        project_id: str,
        setting: AgentAISettingUpdate,
    ) -> AgentAISetting:
        if self.use_fallback:
            rows = self._agent_ai_settings.setdefault(project_id, {})
            existing_cipher = rows.get(setting.agent_name, {}).get("api_key_cipher")
            rows[setting.agent_name] = {
                "provider": setting.provider,
                "model": setting.model,
                "api_key_cipher": (
                    self._encrypt(setting.api_key)
                    if setting.api_key
                    else existing_cipher
                ),
                "updated_at": datetime.utcnow(),
            }
            row = rows[setting.agent_name]
            return AgentAISetting(
                agent_name=setting.agent_name,
                provider=row["provider"],
                model=row["model"],
                api_key_configured=bool(row.get("api_key_cipher")),
                updated_at=row["updated_at"],
            )
        return await self._run_sync(self._save_agent_ai_setting_sync, project_id, setting)

    def _save_agent_ai_setting_sync(
        self,
        project_id: str,
        setting: AgentAISettingUpdate,
    ) -> AgentAISetting:
        api_key_cipher = self._encrypt(setting.api_key) if setting.api_key else None
        with self._connect() as conn:
            with conn.cursor() as cur:
                if api_key_cipher:
                    cur.execute(
                        """
                        INSERT INTO agent_ai_settings
                            (project_id, agent_name, provider, model, api_key_cipher)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            provider = VALUES(provider),
                            model = VALUES(model),
                            api_key_cipher = VALUES(api_key_cipher)
                        """,
                        (
                            project_id,
                            setting.agent_name,
                            setting.provider,
                            setting.model,
                            api_key_cipher,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO agent_ai_settings
                            (project_id, agent_name, provider, model, api_key_cipher)
                        VALUES (%s, %s, %s, %s, NULL)
                        ON DUPLICATE KEY UPDATE
                            provider = VALUES(provider),
                            model = VALUES(model),
                            api_key_cipher = api_key_cipher
                        """,
                        (
                            project_id,
                            setting.agent_name,
                            setting.provider,
                            setting.model,
                        ),
                    )
                cur.execute(
                    """
                    SELECT agent_name, provider, model, api_key_cipher, updated_at
                    FROM agent_ai_settings
                    WHERE project_id = %s AND agent_name = %s
                    """,
                    (project_id, setting.agent_name),
                )
                row = cur.fetchone()
        return AgentAISetting(
            agent_name=row["agent_name"],
            provider=row["provider"],
            model=row["model"],
            api_key_configured=bool(row.get("api_key_cipher")),
            updated_at=row.get("updated_at"),
        )

    async def get_agent_ai_runtime(
        self,
        project_id: str,
        agent_name: str,
    ) -> Optional[dict]:
        if self.use_fallback:
            row = self._agent_ai_settings.get(project_id, {}).get(agent_name)
            if not row:
                return None
            return {
                "provider": row["provider"],
                "model": row["model"],
                "api_key": self._decrypt(row.get("api_key_cipher")),
            }
        return await self._run_sync(self._get_agent_ai_runtime_sync, project_id, agent_name)

    def _get_agent_ai_runtime_sync(
        self,
        project_id: str,
        agent_name: str,
    ) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT provider, model, api_key_cipher
                    FROM agent_ai_settings
                    WHERE project_id = %s AND agent_name = %s
                    """,
                    (project_id, agent_name),
                )
                row = cur.fetchone()
        if not row:
            return None
        return {
            "provider": row["provider"],
            "model": row["model"],
            "api_key": self._decrypt(row.get("api_key_cipher")),
        }


database_manager = DatabaseManager()
