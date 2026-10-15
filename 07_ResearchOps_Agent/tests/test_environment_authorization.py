"""短期环境授权令牌服务测试。"""

from researchops.services import EnvironmentAuthorizationService


def test_environment_authorization_token_is_process_local_and_expiring() -> None:
    service = EnvironmentAuthorizationService(lifetime_seconds=600)
    other_service = EnvironmentAuthorizationService(lifetime_seconds=600)

    grant = service.issue()

    assert service.validate(grant.token) is True
    assert other_service.validate(grant.token) is False
    assert service.validate("not-a-real-token") is False


def test_zero_lifetime_grant_is_immediately_invalid() -> None:
    service = EnvironmentAuthorizationService(lifetime_seconds=0)

    grant = service.issue()

    assert service.validate(grant.token) is False
