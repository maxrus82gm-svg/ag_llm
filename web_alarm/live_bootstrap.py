"""Operator-only composition of the existing Ordinary GigaChat server.

The caller must construct LiveApproval in trusted Python after a specific GO.
Nothing in HTTP, a launcher option, or a serialized configuration mints it.
"""
import asyncio
from pathlib import Path
import threading
import time

import context_storage as core
from gigachat_runtime import LiveApproval, ProviderSession
from ordinary_chat_service import PreSendDenied
from ultra_budget_ledger import BudgetLedger

from .ordinary_provider import OrdinaryProviderFactory
from .server import create_server


def _verified_workspace(api, wa_workspace_id):
    record = api.registry.get(wa_workspace_id)
    root = Path(record.workspace_root).resolve(strict=True)
    identity = core.read_workspace_identity_bounded(root)
    if identity.get("status") != "ok" or root != Path(record.workspace_root):
        raise PreSendDenied("live_workspace_identity_unverified")
    wid = identity["workspace_id"]
    BudgetLedger(root, wid).recover()  # No implicit enrollment or migration.
    return root, wid


def catalog_probe(api, wa_workspace_id, approval, *, tls_context=None):
    """One explicit OAuth/catalog envelope; inference is structurally excluded."""
    if (type(approval) is not LiveApproval or approval.max_oauth != 1
            or approval.max_catalog != 1 or approval.max_inference != 0
            or approval.contracts or not 0 < approval.expires_at - time.time() <= 600):
        raise PreSendDenied("probe_only_approval_required")
    root, wid = _verified_workspace(api, wa_workspace_id)
    session = ProviderSession(root, wid, approval, tls_context=tls_context)
    try:
        return asyncio.run(session.discover_models())
    finally:
        session.close()


def serve_one_inference(api, wa_workspace_id, approval, *, tls_context=None, port=8765):
    """One grant, one Workspace and one existing Web Alarm server process.

    This call is for the later, separate inference GO. It deliberately makes
    the approved catalog call before exposing the chat and never retries it.
    """
    if (type(approval) is not LiveApproval or approval.max_oauth != 1
            or approval.max_catalog != 1 or approval.max_inference != 1
            or len(approval.contracts) != 1 or approval.max_answer_tokens > 32
            or not 0 < approval.expires_at - time.time() <= 900
            or type(port) is not int or not 0 < port < 65536):
        raise PreSendDenied("single_inference_approval_required")
    root, wid = _verified_workspace(api, wa_workspace_id)
    session = ProviderSession(root, wid, approval, tls_context=tls_context)
    server = None
    timer = None
    try:
        factory = OrdinaryProviderFactory.for_session(api.registry, session)
        server = create_server(api, host="127.0.0.1", port=port,
                               ordinary_factory=factory, enable_folder_picker=False)
        # Reserve the local port before spending either approved control call.
        # The server is not serving requests until discovery has succeeded.
        asyncio.run(session.discover_models())
        timer = threading.Timer(max(0, approval.expires_at - time.time()), server.shutdown)
        timer.daemon = True
        timer.start()
        server.serve_forever(poll_interval=0.2)
    finally:
        if timer is not None:
            timer.cancel()
        if server is not None:
            server.server_close()
        session.close()  # A busy/uncertain grant remains fail-closed for review.
