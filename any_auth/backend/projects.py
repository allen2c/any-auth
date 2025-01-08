import json
import logging
import time
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.database
import pymongo.errors

from any_auth.types.pagination import Page
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient, BackendIndexConfig

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

    def create_indexes(
        self, index_configs: typing.Optional[typing.List["BackendIndexConfig"]] = None
    ):
        if index_configs is None:
            index_configs = self._client.settings.indexes_projects

        created_indexes = self.collection.create_indexes(
            [
                pymongo.IndexModel(
                    [(key.field, key.direction) for key in index_config.keys],
                    name=index_config.name,
                    unique=index_config.unique,
                )
                for index_config in index_configs
            ]
        )
        logger.info(f"Created indexes: {created_indexes}")

    def create(
        self,
        project_create: ProjectCreate,
        *,
        organization_id: typing.Text,
        created_by: typing.Text,
    ) -> Project:
        project = project_create.to_project(
            organization_id=organization_id,
            created_by=created_by,
        )
        result = self.collection.insert_one(project.to_doc())
        project._id = str(result.inserted_id)
        logger.info(f"Created project with id {project.id}")
        return project

    def retrieve(self, id: typing.Text) -> typing.Optional[Project]:
        project_data = self.collection.find_one({"id": id})
        if project_data:
            project = Project.model_validate(project_data)
            project._id = str(project_data["_id"])
            logger.debug(f"Retrieved project with id {id}")
            return project
        logger.warning(f"Project with id {id} not found")
        return None

    def retrieve_by_name(self, name: typing.Text) -> typing.Optional[Project]:
        project_data = self.collection.find_one({"name": name})
        if project_data:
            project = Project.model_validate(project_data)
            project._id = str(project_data["_id"])
            logger.debug(f"Retrieved project with name {name}")
            return project
        logger.warning(f"Project with name {name} not found")
        return None

    def list(
        self,
        organization_id: typing.Text,
        *,
        limit: typing.Optional[int] = 20,
        order: typing.Literal["asc", "desc", 1, -1] = -1,
        after: typing.Optional[typing.Text] = None,
        before: typing.Optional[typing.Text] = None,
    ) -> Page[Project]:
        limit = limit or 20
        if limit > 100:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="Limit cannot be greater than 100",
            )

        sort_direction = (
            pymongo.DESCENDING if order in ("desc", -1) else pymongo.ASCENDING
        )

        query: typing.Dict = {"organization_id": organization_id}
        cursor_id = after if after is not None else before
        cursor_type = "after" if after is not None else "before"

        if cursor_id:
            cursor_doc = self.collection.find_one({"id": cursor_id})
            if cursor_doc is None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_404_NOT_FOUND,
                    detail=f"Project with id {cursor_id} not found",
                )
            comparator = (
                "$lt"
                if (
                    (cursor_type == "after" and sort_direction == pymongo.DESCENDING)
                    or (cursor_type == "before" and sort_direction == pymongo.ASCENDING)
                )
                else "$gt"
            )
            query["$or"] = [
                {"created_at": {comparator: cursor_doc["created_at"]}},
                {
                    "created_at": cursor_doc["created_at"],
                    "id": {comparator: cursor_doc["id"]},
                },
            ]

        # Fetch `limit + 1` docs to detect if there's a next/previous page
        logger.debug(
            f"List projects with query: {query}, "
            + f"sort: {sort_direction}, limit: {limit}"
        )
        cursor = (
            self.collection.find(query)
            .sort([("created_at", sort_direction), ("id", sort_direction)])
            .limit(limit + 1)
        )

        docs = list(cursor)
        has_more = len(docs) > limit

        # If we got an extra doc, remove it so we only return `limit` docs
        if has_more:
            docs = docs[:limit]

        # Convert raw MongoDB docs into Project models
        projects: typing.List[Project] = []
        for doc in docs:
            project = Project.model_validate(doc)
            project._id = doc["_id"]
            projects.append(project)

        first_id = projects[0].id if projects else None
        last_id = projects[-1].id if projects else None

        page = Page[Project](
            data=projects,
            first_id=first_id,
            last_id=last_id,
            has_more=has_more,
        )
        return page

    def update(self, id: typing.Text, project_update: ProjectUpdate) -> Project:
        update_data = json.loads(project_update.model_dump_json(exclude_none=True))
        update_data["updated_at"] = int(time.time())

        try:
            updated_doc = self.collection.find_one_and_update(
                {"id": id},
                {"$set": update_data},
                return_document=pymongo.ReturnDocument.AFTER,
            )
        except pymongo.errors.DuplicateKeyError as e:
            raise fastapi.HTTPException(
                status_code=409, detail="A project with this name already exists."
            ) from e

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {id} not found",
            )

        updated_project = Project.model_validate(updated_doc)
        updated_project._id = str(updated_doc["_id"])
        return updated_project

    def set_disabled(self, id: typing.Text, disabled: bool) -> Project:
        updated_doc = self.collection.find_one_and_update(
            {"id": id},
            {"$set": {"disabled": disabled}},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if updated_doc is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {id} not found",
            )

        updated_project = Project.model_validate(updated_doc)
        updated_project._id = str(updated_doc["_id"])
        return updated_project
