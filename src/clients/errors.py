class ProviderUnavailableError(RuntimeError):
    pass


class ProviderConfigurationError(RuntimeError):
    pass


class ParsingRetriesExhaustedError(ProviderUnavailableError):
    pass


class ProviderCredentialError(ProviderUnavailableError, ProviderConfigurationError):
    """Missing or rejected credentials; eligible for provider fallback."""
