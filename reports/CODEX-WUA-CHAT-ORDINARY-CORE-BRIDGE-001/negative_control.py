"""The actual legacy last-pair projection must fail the new full-history oracle."""
import unittest
from unittest.mock import patch
import test_web_alarm_ordinary_core_bridge as bridge
from web_alarm.ultra_chat import OfflineUltraChatService

with patch.object(bridge, "OrdinaryCoreChatService", OfflineUltraChatService):
    suite = unittest.defaultTestLoader.loadTestsFromName(
        "CoreBridgeTests.test_complete_history_and_system_context_use_existing_core", bridge)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
