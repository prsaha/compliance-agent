"""
LLM Abstraction Layer

Provides a unified interface for interacting with different LLM providers
"""

from .base import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMConfig,
    LLMProvider,
    LLMError,
    LLMConnectionError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMInvalidRequestError
)

from .factory import (
    LLMProviderFactory,
    create_llm
)

from .config_manager import (
    LLMConfigManager,
    ConfigEncryption,
    get_llm_from_config
)

from .providers import (
    AnthropicProvider,
    OpenAIProvider,
    GoogleProvider,
    CohereProvider,
    AzureProvider,
    LocalProvider
)

__all__ = [
    # Base classes
    'BaseLLMProvider',
    'LLMMessage',
    'LLMResponse',
    'LLMConfig',
    'LLMProvider',

    # Errors
    'LLMError',
    'LLMConnectionError',
    'LLMAuthenticationError',
    'LLMRateLimitError',
    'LLMTimeoutError',
    'LLMInvalidRequestError',

    # Factory
    'LLMProviderFactory',
    'create_llm',

    # Config management
    'LLMConfigManager',
    'ConfigEncryption',
    'get_llm_from_config',

    # Providers
    'AnthropicProvider',
    'OpenAIProvider',
    'GoogleProvider',
    'CohereProvider',
    'AzureProvider',
    'LocalProvider',
]

__version__ = '1.0.0'
