class AIError(Exception): pass
class ProviderError(AIError): pass
class RateLimitError(ProviderError): pass
class AuthError(ProviderError): pass
class ModelNotFoundError(ProviderError): pass
class NetworkError(AIError): pass
