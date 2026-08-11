from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import langfuse

from app import tracing


class TracingAdapterTests(unittest.TestCase):
    def test_adapter_uses_the_installed_langfuse_v3_api(self) -> None:
        self.assertEqual(tracing._langfuse_observe.__module__, langfuse.observe.__module__)
        client = tracing.get_langfuse_client()
        self.assertTrue(callable(client.update_current_trace))
        self.assertTrue(callable(client.update_current_generation))

    def test_tracing_is_disabled_without_both_keys(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(tracing.tracing_enabled())

        with patch.dict(os.environ, {"LANGFUSE_PUBLIC_KEY": "pk-only"}, clear=True):
            self.assertFalse(tracing.tracing_enabled())

    def test_disabled_tracing_does_not_initialize_langfuse_client(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(tracing, "get_client", side_effect=AssertionError("SDK called")),
        ):
            client = tracing.get_langfuse_client()

        self.assertIsNone(client.get_current_observation_id())
        self.assertIsNone(client.update_current_trace(prompt_version="local-v1"))
        self.assertIsNone(client.update_current_generation(cost=0.0))


if __name__ == "__main__":
    unittest.main()
