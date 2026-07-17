import os
import sys
import unittest
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure conda env is set up
os.environ.setdefault("CONDA_DEFAULT_ENV", r"E:\AI\conda_envs\lumina")

from core.container import container as global_container
from core.interfaces import IMemoryManager, IWorkspaceManager
from lumina import AudioLoop
from memory_store import MemoryStore
from project_manager import ProjectManager


class TestAudioLoopDI(unittest.TestCase):
    def setUp(self):
        # Save initial registration states to restore after each test
        self.initial_mem_store_reg = global_container._registry.get(IMemoryManager)
        self.initial_proj_mgr_reg = global_container._registry.get(IWorkspaceManager)

    def tearDown(self):
        # Restore initial container states
        if self.initial_mem_store_reg is not None:
            global_container._registry[IMemoryManager] = self.initial_mem_store_reg
        else:
            global_container._registry.pop(IMemoryManager, None)
            
        if self.initial_proj_mgr_reg is not None:
            global_container._registry[IWorkspaceManager] = self.initial_proj_mgr_reg
        else:
            global_container._registry.pop(IWorkspaceManager, None)

    def test_explicit_constructor_injection(self):
        """Test explicit constructor injection of dependencies."""
        dummy_memory = object()
        dummy_project = object()
        
        loop = AudioLoop(
            video_mode="none",
            memory_store=dummy_memory,
            project_manager=dummy_project
        )
        
        self.assertIs(loop.memory_store, dummy_memory)
        self.assertIs(loop.project_manager, dummy_project)

    def test_di_container_resolution(self):
        """Test resolution of dependencies from the DI container."""
        dummy_memory = object()
        dummy_project = object()
        
        # Override container registrations
        global_container.override(IMemoryManager, dummy_memory)
        global_container.override(IWorkspaceManager, dummy_project)
        
        loop = AudioLoop(video_mode="none")
        self.assertIs(loop.memory_store, dummy_memory)
        self.assertIs(loop.project_manager, dummy_project)

    def test_backward_compatible_fallback_behavior(self):
        """Test backward-compatible fallback to inline construction if no DI or constructor args are provided."""
        # Clean registrations in the container
        global_container._registry.pop(IMemoryManager, None)
        global_container._registry.pop(IWorkspaceManager, None)
        
        loop = AudioLoop(video_mode="none")
        self.assertIsInstance(loop.memory_store, MemoryStore)
        self.assertIsInstance(loop.project_manager, ProjectManager)


if __name__ == "__main__":
    unittest.main(verbosity=2)
