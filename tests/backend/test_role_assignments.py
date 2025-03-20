import typing

from any_auth.backend import BackendClient
from any_auth.types.organization import Organization
from any_auth.types.project import Project
from any_auth.types.role import Role
from any_auth.types.user import UserInDB


def test_role_assignments_operations(
    deps_backend_client_session_with_all_resources: BackendClient,
    deps_org: Organization,
    deps_project: Project,
    deps_user_newbie: typing.Tuple[UserInDB, typing.Text],
    deps_role_na: Role,
):
    backend_client_session = deps_backend_client_session_with_all_resources
    user, _ = deps_user_newbie

    # Assign project owner role to the newbie user
    backend_client_session.role_assignments.assign_role(
        target_id=user.id,
        role_id=deps_role_na.id,
        resource_id=deps_project.id,
    )

    # Get the role assignments
    role_assignments = backend_client_session.role_assignments.retrieve_by_target_id(
        target_id=user.id, resource_id=deps_project.id
    )
    assert len(role_assignments) == 1
    assert role_assignments[0].role_id == deps_role_na.id

    # Delete the role assignments
    for role_assignment in role_assignments:
        backend_client_session.role_assignments.delete(role_assignment.id)

    # Check that the role assignments are deleted
    assert (
        len(
            backend_client_session.role_assignments.retrieve_by_target_id(
                target_id=user.id, resource_id=deps_project.id
            )
        )
        == 0
    )
