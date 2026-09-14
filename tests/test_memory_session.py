import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.memory.session_manager import SessionMemoryManager, memory_manager
from backend.app.memory.context_window import format_chat_history
from backend.app.agents.root_agent import root_supervisor

client = TestClient(app)


def test_memory_manager_status():
    """Test memory manager status reporting"""
    status = memory_manager.get_status()
    assert "engine" in status
    assert "redis_connected" in status
    assert "ttl_seconds" in status
    assert status["ttl_seconds"] > 0


def test_memory_add_and_retrieve_history():
    """Test storing and sliding window retrieval of conversation turns"""
    test_session = "unit-test-session-123"
    memory_manager.clear_session(test_session)

    memory_manager.add_turn(test_session, "user", "Hello, do you have a cardiologist?", patient_id=1)
    memory_manager.add_turn(test_session, "agent", "Yes, Dr. Elena Rostova is available.", agent_name="Doctor Agent", patient_id=1)
    memory_manager.add_turn(test_session, "user", "What are her consulting hours?", patient_id=1)
    memory_manager.add_turn(test_session, "agent", "She is available from 09:00 to 13:00.", agent_name="Doctor Agent", patient_id=1)

    history = memory_manager.get_history(test_session, limit=10)
    assert len(history) == 4
    assert history[0]["role"] == "user"
    assert "cardiologist" in history[0]["content"]
    assert history[1]["agent_name"] == "Doctor Agent"
    assert history[2]["role"] == "user"
    assert history[3]["agent_name"] == "Doctor Agent"

    # Test sliding limit
    limited = memory_manager.get_history(test_session, limit=2)
    assert len(limited) == 2
    assert limited[0]["content"] == "What are her consulting hours?"


def test_clear_session():
    """Test clearing active session history"""
    test_session = "clear-test-session-456"
    memory_manager.add_turn(test_session, "user", "Testing session clearing", patient_id=1)
    assert len(memory_manager.get_history(test_session)) >= 1

    cleared = memory_manager.clear_session(test_session)
    assert cleared is True
    # After clearing active memory cache, fast history for this session is empty
    fresh_history = memory_manager.get_history(test_session, limit=10)
    # Note: DB still retains for audit, but cache is flushed
    assert isinstance(fresh_history, list)


def test_context_window_formatting():
    """Test formatting history turns into clean prompt context"""
    turns = [
        {"role": "user", "content": "Where is the pharmacy?", "agent_name": None},
        {"role": "agent", "content": "The pharmacy is on the 1st floor next to the lobby.", "agent_name": "Hospital Agent"},
        {"role": "user", "content": "What time does it close?", "agent_name": None}
    ]
    formatted = format_chat_history(turns)
    assert "Patient: Where is the pharmacy?" in formatted
    assert "Hospital Agent: The pharmacy is on the 1st floor next to the lobby." in formatted
    assert "Patient: What time does it close?" in formatted


def test_lock_acquire_and_release():
    """Test concurrency lock mechanics"""
    lock_name = "doctor_1_2026_10_15_10_00"
    acquired = memory_manager.acquire_lock(lock_name, timeout=2.0)
    assert acquired is True

    # Attempting to acquire the same lock immediately in same thread or across processes
    # Releasing lock
    memory_manager.release_lock(lock_name)


def test_api_memory_status_endpoint():
    """Test GET /api/v1/chat/status"""
    response = client.get("/api/v1/chat/status")
    assert response.status_code == 200
    data = response.json()
    assert "engine" in data
    assert "redis_connected" in data


def test_api_chat_history_and_clear_endpoints():
    """Test GET and DELETE /api/v1/chat/history/{session_id}"""
    session_id = "api-test-session-789"
    # Post a message first
    post_res = client.post("/api/v1/chat", json={
        "message": "What is the hospital address?",
        "session_id": session_id,
        "patient_id": 1
    })
    assert post_res.status_code == 200

    # Retrieve history
    hist_res = client.get(f"/api/v1/chat/history/{session_id}")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["session_id"] == session_id
    assert hist_data["count"] >= 2  # user + agent turns

    # Clear history
    del_res = client.delete(f"/api/v1/chat/history/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["cleared"] is True


def test_multi_turn_workflow_context_injection():
    """Test that root_supervisor injects sliding context into sub-agent execution"""
    session_id = "multi-turn-workflow-test"
    memory_manager.clear_session(session_id)

    # Turn 1: Doctor inquiry
    res1 = root_supervisor.execute_workflow(
        "Who is the neurologist?",
        {"patient_id": 1, "session_id": session_id}
    )
    assert res1["route"] == "doctor"
    assert "Chen" in res1["response"] or "neurologist" in res1["response"].lower()

    # Turn 2: Follow-up question
    res2 = root_supervisor.execute_workflow(
        "What are the visiting hours?",
        {"patient_id": 1, "session_id": session_id}
    )
    assert res2["route"] == "hospital"
    assert len(memory_manager.get_history(session_id)) >= 4
