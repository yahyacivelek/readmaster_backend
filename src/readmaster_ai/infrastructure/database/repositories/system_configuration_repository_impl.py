"""
Concrete implementation of the SystemConfigurationRepository interface using SQLAlchemy.
"""
from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert # For upsert functionality
from datetime import datetime, timezone # Ensure timezone is available

from readmaster_ai.domain.entities.system_configuration import SystemConfiguration as DomainSystemConfiguration
from readmaster_ai.domain.repositories.system_configuration_repository import SystemConfigurationRepository
from readmaster_ai.infrastructure.database.models import SystemConfigurationModel
# No ApplicationException needed here unless for very specific repo errors not covered by SQLAlchemy

def _config_model_to_domain(model: SystemConfigurationModel) -> Optional[DomainSystemConfiguration]:
    """Converts a SystemConfigurationModel SQLAlchemy object to a DomainSystemConfiguration entity."""
    if not model:
        return None
    return DomainSystemConfiguration(
        key=model.key,
        value=model.value,  # SQLAlchemy handles JSONB to Python dict/list/primitive
        description=model.description,
        updated_at=model.updated_at # Ensure this is timezone-aware if DB stores it that way
    )

class SystemConfigurationRepositoryImpl(SystemConfigurationRepository):
    """SQLAlchemy implementation of the system configuration repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, key: str) -> Optional[DomainSystemConfiguration]:
        """Retrieves a system configuration setting by its unique key."""
        stmt = select(SystemConfigurationModel).where(SystemConfigurationModel.key == key)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _config_model_to_domain(model)

    async def set_config(self, config: DomainSystemConfiguration) -> DomainSystemConfiguration:
        """
        Creates a new system configuration or updates an existing one (upsert).
        The `updated_at` field is set to the current time by this method.
        """
        current_time = datetime.now(timezone.utc) # Use timezone-aware datetime

        values_to_insert = {
            "key": config.key,
            "value": config.value, # Assumes value is JSON-serializable by SQLAlchemy driver
            "description": config.description,
            "updated_at": current_time # Set on initial insert
        }

        # Using PostgreSQL's ON CONFLICT DO UPDATE for upsert functionality
        stmt = pg_insert(SystemConfigurationModel).values(**values_to_insert)

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[SystemConfigurationModel.key], # Conflict target is the primary key 'key'
            set_={
                "value": stmt.excluded.value, # Use excluded to get value from the new data
                "description": stmt.excluded.description,
                "updated_at": current_time # Update timestamp on conflict as well
            }
        ).returning(SystemConfigurationModel) # Return the inserted or updated row

        db_execution_result = await self.session.execute(upsert_stmt)
        # self.session.flush() # Not typically needed with .returning() + execute for autocommit drivers
        # or if session commit is handled by a unit of work pattern.
        updated_or_inserted_model = db_execution_result.scalar_one()

        domain_entity = _config_model_to_domain(updated_or_inserted_model)
        if not domain_entity: # Should not happen if upsert and mapping are correct
            raise Exception(f"Failed to map SystemConfigurationModel back to domain entity for key {config.key} after upsert.")
        return domain_entity

    async def get_all_configs(self) -> List[DomainSystemConfiguration]:
        """Retrieves all system configuration settings, ordered by key."""
        stmt = select(SystemConfigurationModel).order_by(SystemConfigurationModel.key)
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        domain_configs = [_config_model_to_domain(m) for m in models if _config_model_to_domain(m) is not None]
        return domain_configs
