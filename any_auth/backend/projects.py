import logging
import typing

import pymongo
import pymongo.collection
import pymongo.database

from any_auth.types.project import Project

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class Projects:
    def __init__(self, client: "BackendClient"):
        self._client: typing.Final["BackendClient"] = client
        self.collection_name: typing.Final[typing.Text] = (
            self._client.settings.collection_projects
        )
        self.collection: typing.Final[pymongo.collection.Collection] = (
            self._client.database[self.collection_name]
        )

    def create_project(self, project: Project) -> Project:
        self.collection.insert_one(project.to_doc())
        logger.info(f"Created project with id {project.id}")
        return project

    def retrieve_project(self, project_id: typing.Text) -> typing.Optional[Project]:
        project_data = self.collection.find_one({"id": project_id})
        if project_data:
            project = Project.model_validate(project_data)
            project._id = str(project_data["_id"])
            logger.debug(f"Retrieved project with id {project_id}")
            return project
        logger.warning(f"Project with id {project_id} not found")
        return None

    def update_project(
        self, project_id: typing.Text, updates: typing.Dict[typing.Text, typing.Any]
    ) -> typing.Optional[Project]:
        updated_data = self.collection.find_one_and_update(
            {"id": project_id},
            {"$set": updates},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        if updated_data:
            project = Project.model_validate(updated_data)
            project._id = str(updated_data["_id"])
            logger.info(f"Updated project with id {project_id}")
            return project
        logger.warning(f"Failed to update. Project with id {project_id} not found")
        return None

    def delete_project(self, project_id: typing.Text) -> bool:
        result = self.collection.delete_one({"id": project_id})
        if result.deleted_count > 0:
            logger.info(f"Deleted project with id {project_id}")
            return True
        logger.warning(f"Attempted to delete non-existent project with id {project_id}")
        return False

    def list_projects(
        self, organization_id: typing.Optional[typing.Text] = None, limit: int = 100
    ) -> typing.List[Project]:
        query = {}
        if organization_id:
            query["organization_id"] = organization_id
        projects = list(self.collection.find(query).limit(limit))
        logger.debug(
            f"Listed {len(projects)} projects for organization_id={organization_id}"
        )
        return [Project.model_validate(project) for project in projects]
