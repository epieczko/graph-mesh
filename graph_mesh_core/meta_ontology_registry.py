"""Registry for meta-ontology providers.

This module provides a central registry for managing and instantiating
meta-ontology providers. It supports both built-in providers and
user-defined custom providers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Type

from graph_mesh_core.meta_ontology_base import MetaOntologyProvider

LOGGER = logging.getLogger(__name__)


class MetaOntologyRegistry:
    """Central registry for meta-ontology providers.

    The registry maintains a mapping of provider names to provider classes,
    and provides factory methods for creating provider instances from configuration.

    Example:
        >>> # Use built-in provider
        >>> provider = MetaOntologyRegistry.create({"type": "generic"})
        >>>
        >>> # Use provider with options
        >>> provider = MetaOntologyRegistry.create({
        ...     "type": "fibo",
        ...     "options": {"modules": ["FND", "LOAN"]}
        ... })
        >>>
        >>> # Register custom provider
        >>> MetaOntologyRegistry.register("mydomain", MyCustomProvider)
        >>> provider = MetaOntologyRegistry.create({"type": "mydomain"})
    """

    _providers: Dict[str, Type[MetaOntologyProvider]] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls):
        """Lazy initialization of built-in providers."""
        if cls._initialized:
            return

        # Import here to avoid circular dependencies
        try:
            from graph_mesh_core.providers.generic import GenericMetaOntology

            cls._providers["generic"] = GenericMetaOntology
            LOGGER.debug("Registered built-in provider: generic")
        except ImportError as e:
            LOGGER.warning("Could not register generic provider: %s", e)

        try:
            from graph_mesh_core.providers.fibo import FIBOMetaOntology

            cls._providers["fibo"] = FIBOMetaOntology
            LOGGER.debug("Registered built-in provider: fibo")
        except ImportError as e:
            LOGGER.debug("FIBO provider not available: %s", e)

        try:
            from graph_mesh_core.providers.custom import CustomMetaOntology

            cls._providers["custom"] = CustomMetaOntology
            LOGGER.debug("Registered built-in provider: custom")
        except ImportError as e:
            LOGGER.warning("Could not register custom provider: %s", e)

        try:
            from graph_mesh_core.providers.composite import CompositeMetaOntology

            cls._providers["composite"] = CompositeMetaOntology
            LOGGER.debug("Registered built-in provider: composite")
        except ImportError as e:
            LOGGER.debug("Composite provider not available: %s", e)

        cls._initialized = True

    @classmethod
    def register(cls, name: str, provider_class: Type[MetaOntologyProvider]) -> None:
        """Register a new meta-ontology provider.

        Args:
            name: Unique identifier for the provider (used in manifest 'type' field)
            provider_class: Class implementing MetaOntologyProvider interface

        Raises:
            TypeError: If provider_class doesn't implement MetaOntologyProvider
            ValueError: If name is already registered

        Example:
            >>> class MyOntology(MetaOntologyProvider):
            ...     # implement interface
            ...     pass
            >>>
            >>> MetaOntologyRegistry.register("myonto", MyOntology)
        """
        cls._ensure_initialized()

        if not issubclass(provider_class, MetaOntologyProvider):
            raise TypeError(
                f"Provider class must implement MetaOntologyProvider interface, "
                f"got {provider_class}"
            )

        if name in cls._providers:
            LOGGER.warning("Overwriting existing provider registration: %s", name)

        cls._providers[name] = provider_class
        LOGGER.info("Registered meta-ontology provider: %s", name)

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a provider.

        Args:
            name: Provider name to remove

        Raises:
            KeyError: If provider name is not registered
        """
        cls._ensure_initialized()

        if name not in cls._providers:
            raise KeyError(f"Provider not registered: {name}")

        del cls._providers[name]
        LOGGER.info("Unregistered meta-ontology provider: %s", name)

    @classmethod
    def create(cls, config: Dict[str, Any]) -> MetaOntologyProvider:
        """Create a meta-ontology provider from configuration.

        Args:
            config: Configuration dictionary with structure:
                {
                    "type": "provider_name",  # required
                    "options": {              # optional, provider-specific
                        "key": "value",
                        ...
                    }
                }

        Returns:
            Instantiated MetaOntologyProvider

        Raises:
            ValueError: If provider type is unknown or config is invalid
            TypeError: If options are not compatible with provider

        Example:
            >>> # Simple provider
            >>> config = {"type": "generic"}
            >>> provider = MetaOntologyRegistry.create(config)
            >>>
            >>> # Provider with options
            >>> config = {
            ...     "type": "fibo",
            ...     "options": {
            ...         "modules": ["FND", "LOAN"],
            ...         "cache_dir": "./fibo_cache"
            ...     }
            ... }
            >>> provider = MetaOntologyRegistry.create(config)
        """
        cls._ensure_initialized()

        if not isinstance(config, dict):
            raise ValueError(f"Config must be a dictionary, got {type(config)}")

        provider_type = config.get("type")
        if not provider_type:
            raise ValueError("Config must specify 'type' field")

        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            available = ", ".join(cls.list_providers())
            raise ValueError(
                f"Unknown meta-ontology provider: '{provider_type}'. "
                f"Available providers: {available}"
            )

        options = config.get("options", {})
        if not isinstance(options, dict):
            raise ValueError(f"Config 'options' must be a dictionary, got {type(options)}")

        try:
            LOGGER.info(
                "Creating meta-ontology provider: %s with options: %s",
                provider_type,
                options,
            )
            provider = provider_class(**options)
            return provider
        except TypeError as e:
            raise TypeError(
                f"Failed to instantiate provider '{provider_type}' with options {options}: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error creating provider '{provider_type}': {e}"
            ) from e

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names (strings) that can be used in config 'type' field.

        Example:
            >>> providers = MetaOntologyRegistry.list_providers()
            >>> print(f"Available: {', '.join(providers)}")
            Available: generic, fibo, custom, composite
        """
        cls._ensure_initialized()
        return sorted(cls._providers.keys())

    @classmethod
    def get_provider_class(cls, name: str) -> Type[MetaOntologyProvider]:
        """Get the provider class for a given name.

        Args:
            name: Provider name

        Returns:
            Provider class

        Raises:
            KeyError: If provider name is not registered
        """
        cls._ensure_initialized()

        if name not in cls._providers:
            available = ", ".join(cls.list_providers())
            raise KeyError(
                f"Provider '{name}' not found. Available: {available}"
            )

        return cls._providers[name]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider name is registered.

        Args:
            name: Provider name to check

        Returns:
            True if provider is registered, False otherwise.
        """
        cls._ensure_initialized()
        return name in cls._providers

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (mainly for testing).

        Clears all registered providers and resets initialization state.
        Built-in providers will be re-registered on next access.
        """
        cls._providers.clear()
        cls._initialized = False
        LOGGER.debug("Registry reset")
