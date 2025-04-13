import json
import logging
import time
import typing

import fastapi
import pymongo
import pymongo.collection
import pymongo.database
import pymongo.errors

from any_auth.backend._base import BaseCollection
from any_auth.types.pagination import Page
from any_auth.types.project import Project, ProjectCreate, ProjectUpdate

if typing.TYPE_CHECKING:
    from any_auth.backend._client import BackendClient

logger = logging.getLogger(__name__)


class Projects(BaseCollection):
    def __init__(self, client: "BackendClient"):
        super().__init__(client)

    @property
    def collection_name(self):
        return "projects"

    def create_indexes(self, *args, **kwargs):
        super().create_indexes(self.settings.indexes_projects)

    def create(
        self,
        project_create: ProjectCreate,
        *,
        organization_id: typing.Text | None = None,
        created_by: typing.Text,
    ) -> Project:
        project = project_create.to_project(
            organization_id=organization_id,
            created_by=created_by,
        )
        result = self.collection.insert_one(project.to_doc())
        project._id = str(result.inserted_id)
        logger.info(f"Created project with id {project.id}")

        # Delete cache
        self._client.cache.delete(f"project:{project.id}")

        return project

    def retrieve(self, id: typing.Text) -> typing.Optional[Project]:
        # Get from cache
        cached_project = self._client.cache.get(f"project:{id}")
        if cached_project:
            return Project.model_validate_json(cached_project)  # type: ignore

        project_data = self.collection.find_one({"id": id})
        if project_data:
            project = Project.model_validate(project_data)
            project._id = str(project_data["_id"])
            logger.debug(f"Retrieved project with id {id}")

            # Cache
            self._client.cache.set(
                f"project:{id}",
                project.model_dump_json(),
                self._client.cache_ttl,
            )

            return project
        logger.warning(f"Project with id {id} not found")
        return None

    def retrieve_by_name(self, name: typing.Text) -> typing.Optional[Project]:
        # Get from cache
        cached_project = self._client.cache.get(f"project_by_name:{name}")
        if cached_project:
            return Project.model_validate_json(cached_project)  # type: ignore

        project_data = self.collection.find_one({"name": name})
        if project_data:
            project = Project.model_validate(project_data)
            project._id = str(project_data["_id"])
            logger.debug(f"Retrieved project with name {name}")

            # Cache
            self._client.cache.set(
                f"project_by_name:{name}",
                project.model_dump_json(),
                self._client.cache_ttl,
            )

            return project
        logger.warning(f"Project with name {name} not found")
        return None

    def retrieve_by_ids(self, ids: typing.List[str]) -> typing.List[Project]:
        cursor = self.collection.find({"id": {"$in": ids}})
        out: typing.List[Project] = []
        for doc in cursor:
            project = Project.model_validate(doc)
            project._id = str(doc["_id"])
            out.append(project)
        return out

    def list(
        self,
        *,
        organization_id: typing.Text | None = None,
        no_organization: bool = False,
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

        query: typing.Dict = {}
        if no_organization:
            query["organization_id"] = None
        elif organization_id is not None:
            query["organization_id"] = organization_id

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
            query["_id"] = {comparator: cursor_doc["_id"]}

        # Fetch `limit + 1` docs to detect if there's a next/previous page
        logger.debug(
            f"List projects with query: {query}, "
            + f"sort: {sort_direction}, limit: {limit}"
        )
        cursor = (
            self.collection.find(query).sort([("_id", sort_direction)]).limit(limit + 1)
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

        # Delete cache
        self._client.cache.delete(f"project:{updated_project.id}")

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

        # Delete cache
        self._client.cache.delete(f"project:{updated_project.id}")

        return updated_project
