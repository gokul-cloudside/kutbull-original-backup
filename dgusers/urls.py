from rest_framework_nested import routers
from dgusers.views import UserView, OrganizationUserView, RoleMatrixView

router = routers.SimpleRouter()
router.register(r'users', UserView, base_name="users")
router.register(r'organization_users', OrganizationUserView, base_name="organization_users")
router.register(r'role_matrix', RoleMatrixView, base_name="role_matrix")