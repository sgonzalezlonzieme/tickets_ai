class ProviderUnavailableError(RuntimeError):
    pass


class ProviderConfigurationError(RuntimeError):
    pass


class ParsingRetriesExhaustedError(ProviderUnavailableError):
    pass
