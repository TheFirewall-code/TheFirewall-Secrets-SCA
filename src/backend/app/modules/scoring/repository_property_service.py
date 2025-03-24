from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from app.modules.scoring.model.model import (
    BusinessCriticality,
    Environment,
    DataSensitivity,
    RegulatoryRequirement,
)
from app.modules.scoring.schema.schema import PropertyType, PropertyCreate, PropertyUpdate, AttachPropertyRequest
from app.modules.repository.models.repository import Repo
from typing import List, Type, Dict
from sqlalchemy.exc import IntegrityError


class RepositoryPropertyService:

    @staticmethod
    async def init_default_values(db: AsyncSession):

        try:
            """
            Initialize default values for each property type if they don't already exist.
            """
            await RepositoryPropertyService._init_defaults_for_model(db, BusinessCriticality, [
                {"name": "Critical", "value": 1.0},
                {"name": "High", "value": 0.75},
                {"name": "Medium", "value": 0.5},
                {"name": "Low", "value": 0.25}
            ])

            await RepositoryPropertyService._init_defaults_for_model(db, Environment, [
                {"name": "Production", "value": 1.0},
                {"name": "Staging", "value": 0.75},
                {"name": "Development", "value": 0.5},
                {"name": "Testing", "value": 0.25}
            ])

            await RepositoryPropertyService._init_defaults_for_model(db, DataSensitivity, [
                {"name": "Highly Sensitive", "value": 1.0},
                {"name": "Sensitive", "value": 0.75},
                {"name": "Internal", "value": 0.5},
                {"name": "Public", "value": 0.25}
            ])

            await RepositoryPropertyService._init_defaults_for_model(db, RegulatoryRequirement, [
                {"name": "PCI-DSS", "value": 1.0},
                {"name": "HIPAA", "value": 1.0},
                {"name": "GDPR", "value": 1.0}
            ])
        except Exception as e:
            print("Entries already created")

    @staticmethod
    async def _init_defaults_for_model(
            db: AsyncSession,
            model: Type,
            default_values: List[dict]):
        """
        Insert default values for a model if they don't already exist.
        """
        for entry in default_values:
            await RepositoryPropertyService._get_or_create(db, model, **entry)

    @staticmethod
    async def _get_or_create(db: AsyncSession, model: Type, **kwargs):
        """
        Asynchronously fetch an existing instance or create a new one.
        """
        stmt = select(model).filter_by(**kwargs)
        result = await db.execute(stmt)
        instance = result.scalars().first()

        if not instance:
            instance = model(**kwargs)
            db.add(instance)
            await db.commit()
            await db.refresh(instance)

        return instance

    @staticmethod
    def _get_model(property_type: PropertyType) -> Type:
        """
        Return the appropriate model for the given property type.
        """
        models = {
            PropertyType.BUSINESS_CRITICALITY: BusinessCriticality,
            PropertyType.ENVIRONMENT: Environment,
            PropertyType.DATA_SENSITIVITY: DataSensitivity,
            PropertyType.REGULATORY_REQUIREMENT: RegulatoryRequirement,
        }
        return models[property_type]

    @staticmethod
    async def get_properties(db: AsyncSession, property_type: PropertyType):
        """
        Asynchronously get all properties of a given type.
        """
        model = RepositoryPropertyService._get_model(property_type)
        stmt = select(model)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_property(
            db: AsyncSession,
            property_type: PropertyType,
            data: PropertyCreate):
        """
        Create a new property.
        """
        model = RepositoryPropertyService._get_model(property_type)
        instance = model(**data.dict())
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    @staticmethod
    async def update_property(
            db: AsyncSession,
            property_type: PropertyType,
            property_id: int,
            data: PropertyUpdate):
        """
        Update an existing property.
        """
        model = RepositoryPropertyService._get_model(property_type)
        instance = await RepositoryPropertyService._get_instance(db, model, id=property_id)
        for key, value in data.dict(exclude_unset=True).items():
            setattr(instance, key, value)
        await db.commit()
        return instance

    # @staticmethod
    # async def delete_property(db: AsyncSession, property_type: PropertyType, property_id: int):
    #     """
    #     Delete a property.
    #     """
    #     model = RepositoryPropertyService._get_model(property_type)
    #     instance = await RepositoryPropertyService._get_instance(db, model, id=property_id)
    #     await db.delete(instance)
    #     await db.commit()

    @staticmethod
    async def attach_property_to_repo(
            db: AsyncSession,
            repo_id: int,
            request: AttachPropertyRequest):
        """
        Attach a property to a repository.
        """
        repo = await RepositoryPropertyService._get_instance(db, Repo, id=repo_id)

        if request.property_type == PropertyType.BUSINESS_CRITICALITY:
            repo.criticality_id = request.property_id
        elif request.property_type == PropertyType.ENVIRONMENT:
            repo.environment_id = request.property_id
        elif request.property_type == PropertyType.DATA_SENSITIVITY:
            repo.sensitivity_id = request.property_id
        elif request.property_type == PropertyType.REGULATORY_REQUIREMENT:
            repo.regulation_id = request.property_id

        await db.commit()
        await db.refresh(repo)

    @staticmethod
    async def remove_property_from_repo(
            db: AsyncSession,
            repo_id: int,
            property_type: PropertyType):
        """
        Remove a property from a repository by setting its foreign key to None.
        """
        repo = await RepositoryPropertyService._get_instance(db, Repo, id=repo_id)

        if property_type == PropertyType.BUSINESS_CRITICALITY:
            repo.criticality_id = None
        elif property_type == PropertyType.ENVIRONMENT:
            repo.environment_id = None
        elif property_type == PropertyType.DATA_SENSITIVITY:
            repo.sensitivity_id = None
        elif property_type == PropertyType.REGULATORY_REQUIREMENT:
            repo.regulation_id = None

        await db.commit()
        await db.refresh(repo)

    @staticmethod
    async def _get_instance(db: AsyncSession, model: Type, **kwargs):
        """
        Fetch an instance of the given model.
        """
        stmt = select(model).filter_by(**kwargs)
        result = await db.execute(stmt)
        instance = result.scalars().first()
        if not instance:
            raise NoResultFound(f"{model.__name__} not found.")
        return instance

    @staticmethod
    async def get_repo_properties(
            db: AsyncSession, repo_id: int) -> Dict[str, dict]:
        """
        Get all associated properties of a given repository by repo_id.
        """
        repo = await RepositoryPropertyService._get_instance(db, Repo, id=repo_id)

        # Fetch associated properties based on foreign keys
        result = {}
        if repo.criticality_id:
            result['business_criticality'] = await RepositoryPropertyService._get_instance(
                db, BusinessCriticality, id=repo.criticality_id
            )

        if repo.environment_id:
            result['environment'] = await RepositoryPropertyService._get_instance(
                db, Environment, id=repo.environment_id
            )

        if repo.sensitivity_id:
            result['data_sensitivity'] = await RepositoryPropertyService._get_instance(
                db, DataSensitivity, id=repo.sensitivity_id
            )

        if repo.regulation_id:
            result['regulatory_requirement'] = await RepositoryPropertyService._get_instance(
                db, RegulatoryRequirement, id=repo.regulation_id
            )

        return {key: value.__dict__ for key, value in result.items()}
